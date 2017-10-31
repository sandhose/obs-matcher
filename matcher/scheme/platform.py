from datetime import datetime

from slugify import slugify

from ..app import db
from .mixins import ResourceMixin
from .utils import CustomEnum


class PlatformGroup(db.Model, ResourceMixin):
    """A group of platform

    For example, the “Netflix” group would hold all it's country variations
    """
    __tablename__ = 'platform_group'

    id = db.Column(db.Integer,
                   db.Sequence('platform_group_id_seq'),
                   primary_key=True)
    name = db.Column(db.Text,
                     nullable=False)

    platforms = db.relationship('Platform',
                                back_populates='group')

    def __repr__(self):
        return '<PlatformGroup "{}">'.format(self.name)


def slug_default(context):
    """Automatically slugify the platform's name"""
    if context and 'name' in context.current_parameters:
        return slugify(context.current_parameters['name'])
    else:
        return None


class Platform(db.Model, ResourceMixin):
    """Represents one platform"""

    __tablename__ = 'platform'

    id = db.Column(db.Integer,
                   db.Sequence('platform_id_seq'),
                   primary_key=True)
    name = db.Column(db.Text,
                     nullable=False)
    """A human readable name"""

    # FIXME: should be unique
    slug = db.Column(db.Text,
                     nullable=False,
                     default=slug_default)
    """A unique identifier"""

    group_id = db.Column(db.Integer,
                         db.ForeignKey('platform_group.id'))

    # FIXME: way to map ExternalID -> URL
    url = db.Column(db.Text)
    """Base URL of this platform"""

    country = db.Column(db.String(2))
    """ISO 3166-1 alpha-2 country code"""

    max_rating = db.Column(db.Integer, default=10)
    """The max rating for this platform

    As ratings are integers, this should be scaled up to keep precision
    i.e. 47 could represent a score of 4.7/5 stars
    """
    base_score = db.Column(db.Integer, nullable=False, default=100)

    group = db.relationship('PlatformGroup',
                            back_populates='platforms')
    """The group in which this platform is"""

    scraps = db.relationship('Scrap',
                             back_populates='platform')
    """The scraps (to be) done for this platform"""

    links = db.relationship('ObjectLink',
                            back_populates='platform')
    """All known objects found on this platform"""

    def __repr__(self):
        return '<Platform {!r}>'.format(self.name)

    @classmethod
    def lookup(cls, platform):
        """Search for a platform using its ID or Slug

        :platform: Slug or ID of the platform
        :returns: The platform found (None if not found)
        """

        # If platform is already a Platform, just return it
        if isinstance(platform, cls):
            return platform

        try:
            # Try converting into an ID first
            q = Platform.query.filter(Platform.id == int(platform))
        except:
            # then try to match the slug
            q = Platform.query.filter(Platform.slug == platform)

        try:
            return q.one()
        except:
            # Return None if object wasn't found
            return None


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


class ScrapType(CustomEnum):
    # FIXME: Other types of scraps? Like “new releases” pages?
    INDIVIDUAL = 1
    """One job to scrap a bunch of given IDs"""

    FULL = 2
    """Start a full site scrap"""


class Scrap(db.Model, ResourceMixin):
    """Represents one job

    This is used by the scheduler to run the scrapers on SCHEDULED jobs, and
    create new jobs when needed
    """

    __tablename__ = 'scrap'

    id = db.Column(db.Integer,
                   db.Sequence('scrap_id_seq'),
                   primary_key=True)
    platform_id = db.Column(db.Integer,
                            db.ForeignKey('platform.id'),
                            nullable=False)

    date = db.Column(db.DateTime)
    """Date when the scrap was started"""

    status = db.Column(db.Enum(ScrapStatus),
                       nullable=False,
                       default=ScrapStatus.SCHEDULED)
    """Current status of this job, see ScrapStatus"""

    platform = db.relationship('Platform',
                               back_populates='scraps')
    """Platform concerned by this job"""

    links = db.relationship('ObjectLink',
                            secondary='scrap_link',
                            back_populates='scraps')
    """Objects (to be) fetched by this job"""

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
            # FIXME: custom exception
            raise Exception('scrap is "{}", should be "{}"'.format(
                self.status, ScrapStatus.RUNNING))

        if not any(s == status for s in [ScrapStatus.SUCCESS,
                                         ScrapStatus.FAILED,
                                         ScrapStatus.ABORTED]):
            # FIXME: custom exception
            raise Exception('"{}" is not a finished state'.format(status))

        self.status = status

    def run(self):
        """Mark the job as running"""
        if self.status is not ScrapStatus.SCHEDULED:
            # FIXME: custom exception
            raise Exception()

        self.date = datetime.now()
        self.status = ScrapStatus.RUNNING

    def reschedule(self):
        """Reschedule a job"""

        # FIXME: This maybe should duplicate itself when not RUNNING or ABORTED
        if self.status is ScrapStatus.SUCCESS or \
           self.status is ScrapStatus.SCHEDULED:
            # FIXME: custom exception
            raise Exception()

        self.status = ScrapStatus.SCHEDULED

    def __repr__(self):
        return '<Scrap ({}, {})>'.format(self.platform, self.date)
