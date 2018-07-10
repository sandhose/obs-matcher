from datetime import datetime

from slugify import slugify
from sqlalchemy import (Boolean, Column, DateTime, Enum, ForeignKey, Integer,
                        Sequence, String, Text, UniqueConstraint, column, func,
                        select, table,)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import column_property, relationship

from matcher.exceptions import InvalidStatusTransition

from . import Base
from .utils import CustomEnum


class PlatformGroup(Base):
    """A group of platform

    For example, the “Netflix” group would hold all it's country variations
    """
    __tablename__ = 'platform_group'

    platform_group_id_seq = Sequence('platform_group_id_seq', metadata=Base.metadata)
    id = Column(Integer,
                platform_group_id_seq,
                server_default=platform_group_id_seq.next_value(),
                primary_key=True)
    name = Column(Text, nullable=False)

    platforms = relationship('Platform', back_populates='group')

    def __repr__(self):
        return '<PlatformGroup "{}">'.format(self.name)

    def __str__(self):
        return self.name


def slug_default(context):
    """Automatically slugify the platform's name"""
    if context and 'name' in context.current_parameters:
        return slugify(context.current_parameters['name'])
    else:
        return None


class PlatformType(CustomEnum):
    INFO = 1  # Platforms like IMDb
    GLOBAL = 2  # Platforms for global IDs
    TVOD = 3  # Renting VOD
    SVOD = 4  # Subscription based VOD


class Platform(Base):
    """Represents one platform"""

    __tablename__ = 'platform'

    __table_args__ = (
        UniqueConstraint('slug'),
    )

    platform_id_seq = Sequence('platform_id_seq', metadata=Base.metadata)
    id = Column(Integer, platform_id_seq, server_default=platform_id_seq.next_value(), primary_key=True)
    name = Column(Text, nullable=False)
    """A human readable name"""

    # FIXME: should be unique
    slug = Column(Text, nullable=False, default=slug_default)
    """A unique identifier"""

    group_id = Column(Integer, ForeignKey('platform_group.id'))
    """True if a single item can have multiple links within the platform"""
    allow_links_overlap = Column(Boolean, nullable=False, server_default="FALSE")
    """Automatically exclude this platform from exports"""
    ignore_in_exports = Column(Boolean, nullable=False, server_default="FALSE")

    # FIXME: way to map ExternalID -> URL
    url = Column(JSONB)
    """Base URL of this platform"""

    country = Column(String(2))
    """ISO 3166-1 alpha-2 country code"""

    type = Column(
        Enum(PlatformType), nullable=False, default=PlatformType.INFO, server_default='INFO')

    base_score = Column(Integer, nullable=False, default=100)

    group = relationship('PlatformGroup', back_populates='platforms')
    """The group in which this platform is"""

    scraps = relationship('Scrap', back_populates='platform', cascade='all, delete-orphan')
    """The scraps (to be) done for this platform"""

    links = relationship('ObjectLink', back_populates='platform', cascade='all, delete-orphan')
    """All known objects found on this platform"""

    links_count = column_property(
        select([func.count('external_object_id')]).
        select_from(table('object_link')).
        where(column('platform_id') == id)
    )

    def __repr__(self):
        return '<Platform {!r}>'.format(self.name)

    @classmethod
    def lookup(cls, session, platform):
        """Search for a platform using its ID or Slug

        :platform: Slug or ID of the platform
        :returns: The platform found (None if not found)
        """

        # If platform is already a Platform, just return it
        if isinstance(platform, cls):
            return platform

        try:
            # Try converting into an ID first
            q = session.query(Platform).filter(Platform.id == int(platform))
        except ValueError:
            # then try to match the slug
            q = session.query(Platform).filter(Platform.slug == platform)

        return q.one_or_none()

    def match_objects(self):
        """Try to match objects that where found in this platform"""
        from ..scheme.object import ExternalObject

        objs = [l.external_object for l in self.links]
        ExternalObject.match_objects(objs)


class ScrapStatus(CustomEnum):
    """Enum representing the current status of a given scrap"""

    SCHEDULED = 1
    """The job isn't started, and waiting to be picked up"""

    RUNNING = 2
    """The job has been picked up by a worker"""

    ABORTED = 3
    """The job was aborted while running or pending"""

    SUCCESS = 4
    """The job has succedded"""

    FAILED = 5
    """The job has failed"""


class Scrap(Base):
    """Represents one job

    This is used by the scheduler to run the scrapers on SCHEDULED jobs, and
    create new jobs when needed
    """

    __tablename__ = 'scrap'

    scrap_id_seq = Sequence('scrap_id_seq', metadata=Base.metadata)
    id = Column(Integer, scrap_id_seq, server_default=scrap_id_seq.next_value(), primary_key=True)
    platform_id = Column(Integer, ForeignKey('platform.id'), nullable=False)

    date = Column(DateTime)
    """Date when the scrap was started"""

    status = Column(Enum(ScrapStatus), nullable=False, default=ScrapStatus.SCHEDULED)
    """Current status of this job, see ScrapStatus"""

    stats = Column(JSONB)
    """Statistics from scrapy"""

    platform = relationship('Platform', back_populates='scraps')
    """Platform concerned by this job"""

    links = relationship('ObjectLink', secondary='scrap_link', back_populates='scraps')
    """Objects (to be) fetched by this job"""

    links_count = column_property(
        select([func.count('object_link_id')]).
        select_from(table('scrap_link')).
        where(column('scrap_id') == id)
    )

    def to_status(self, status):
        """Try to change the status of the scrap

        It might raise an exception if the transition is invalid

        :status: the state it should transition to
        """
        if self.status is not status:
            if status is ScrapStatus.RUNNING:
                self.run()
            elif status is ScrapStatus.SCHEDULED:
                self.reschedule()
            else:
                self.finish(status)

    def finish(self, status):
        """Set the status to one of the finished status"""
        if self.status is not ScrapStatus.RUNNING:
            raise InvalidStatusTransition(from_status=self.status, to_status=status)

        if not any(s == status
                   for s in [ScrapStatus.SUCCESS, ScrapStatus.FAILED, ScrapStatus.ABORTED]):
            # FIXME: custom exception
            raise Exception('"{}" is not a finished state'.format(status))

        self.status = status

    def run(self):
        """Mark the job as running"""
        if self.status is not ScrapStatus.SCHEDULED:
            raise InvalidStatusTransition(from_status=self.status, to_status=ScrapStatus.RUNNING)

        self.date = datetime.now()
        self.status = ScrapStatus.RUNNING

    def reschedule(self):
        """Reschedule a job"""

        # FIXME: This maybe should duplicate itself when not RUNNING or ABORTED
        if self.status is ScrapStatus.SUCCESS or \
           self.status is ScrapStatus.SCHEDULED or \
           self.status is ScrapStatus.RUNNING:
            raise InvalidStatusTransition(from_status=self.status, to_status=ScrapStatus.SCHEDULED)

        self.status = ScrapStatus.SCHEDULED

    def match_objects(self):
        """Try to match objects that where found in this scrap"""
        from ..scheme.object import ExternalObject

        objs = [l.external_object for l in self.links]
        ExternalObject.match_objects(objs)

    def __repr__(self):
        return '<Scrap ({}, {})>'.format(self.platform, self.date)
