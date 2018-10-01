# -*- coding: utf-8 -*-
"""ExternalObject related models, for handling object manipulation.

This module contains many SQLAlchemy models to insert, merge, and link scrapped
objects together. Everything is built around the :obj:`ExternalObject` model,
which has a type (:obj:`ExternalObjectType`), links to
:obj:`.platform.Platform` (:obj:`ObjectLink`), with models specific to each
:obj:`ExternalObjectType` to store metadatas like relationships (see
:obj:`ExternalObjectMetaMixin`) or episode number.

"""
import collections
import itertools
import math
import re
from operator import attrgetter, itemgetter

from sqlalchemy import (Column, Enum, ForeignKey, Integer,
                        PrimaryKeyConstraint, Sequence, Table, Text, and_,
                        column, func, select, table, tuple_,)
from sqlalchemy.ext.declarative import declared_attr
from sqlalchemy.orm import (aliased, column_property, foreign, joinedload,
                            relationship,)
from sqlalchemy.orm.session import object_session
from tqdm import tqdm
from unidecode import unidecode

from matcher.exceptions import (AmbiguousLinkError, ExternalIDMismatchError,
                                InvalidMetadata, InvalidMetadataValue,
                                InvalidRelation, LinkNotFound, LinksOverlap,
                                ObjectTypeMismatchError, UnknownAttribute,
                                UnknownRelation,)
from matcher.utils import Lock

from .base import Base
from .enums import (ExternalObjectType, Gender, PlatformType, RoleType,
                    ValueType,)

# FIXME: this is an ugly wrapper to lazy-load the session. This file should
# *not* depend on the session therefore it should be passed as an parameter of
# each method that uses it.


class db_(object):
    @property
    def session(self):
        from matcher.app import db
        return db.session


db = db_()


lookup_lock = Lock('lookup')
links_lock = Lock('links')
role_lock = Lock('role')
attributes_lock = Lock('attribute')


scrap_link = Table(
    'scrap_link',
    Base.metadata,
    Column('scrap_id',
           ForeignKey('scrap.id', ondelete='CASCADE', onupdate='CASCADE'),
           primary_key=True),
    Column('object_link_id',
           ForeignKey('object_link.id',
                      ondelete='CASCADE',
                      onupdate='CASCADE'),
           primary_key=True),
)


def create_relationship(relation, parent, child):
    """Create a relationship between two :obj:`ExternalObject`.

    Parameters
    ----------
    relation : str
        the type of relationship to create
    parent : ExternalObject
        the parent object
    child : ExternalObject
        the child object

    """
    relationship_map = {
        'played in': lambda parent, child:
            child.related_object.add_role(parent, role=RoleType.ACTOR),
        'featured': lambda parent, child:
            parent.related_object.add_role(child, role=RoleType.ACTOR),

        'directed': lambda parent, child:
            child.related_object.add_role(parent, role=RoleType.DIRECTOR),
        'directed by': lambda parent, child:
            parent.related_object.add_role(child, role=RoleType.DIRECTOR),

        'wrote': lambda parent, child:
            child.related_object.add_role(parent, role=RoleType.WRITER),
        'wrote by': lambda parent, child:
            parent.related_object.add_role(child, role=RoleType.WRITER),

        'part of': lambda parent, child:
            child.related_object.set_parent(parent),
        'contains': lambda parent, child:
            parent.related_object.set_parent(child),
    }

    try:
        relationship_map[relation](parent, child)
    except KeyError:
        raise UnknownRelation(relation)


external_object_meta_map = {}
"""Maps ExternalObjectTypes to ExternalObjectMetaMixin classes."""


def deduplicate(items, f=lambda x: x):
    seen = set()
    for item in items:
        if not f(item) in seen:
            seen.add(f(item))
            yield item


def _normalize_attribute(type, values):
    if not isinstance(values, list):
        values = [values]

    for value in values:
        if value is None:
            continue

        if isinstance(value, (str, int, float)):
            value = {'text': str(value), 'score_factor': 1}

        yield {'type': type, **value}

        # Try a formatted version of the attribute
        fmt = ValueType.from_name(type).fmt(str(value['text']))
        if fmt is not None:
            yield {'type': type, **value, 'text': fmt}


def _normalize_link(link):
    """Map a link to a (platform, external_id) tuple."""
    from .platform import Platform

    if isinstance(link, tuple):
        # arg can already be a tuple…
        (platform, external_id) = link
    else:
        # …or a dict
        platform = link.get('platform', None)
        external_id = link.get('external_id', None)
        if external_id is None:
            external_id = link.get('id', None)

    # We check if the platform exists (if this doesn't crush
    # performance)
    platform = Platform.lookup(db.session, platform)
    if platform is None:
        # TODO: custom exception
        raise Exception('platform not found')
    else:
        platform_id = platform.id

    return (int(platform_id), str(external_id))


MergeCandidate = collections.namedtuple('MergeCandidate', 'obj into score')


class ExternalObject(Base):
    """An object imported from scraping."""

    __tablename__ = 'external_object'

    external_object_id_seq = Sequence('external_object_id_seq', metadata=Base.metadata)
    id = Column(Integer,
                external_object_id_seq,
                server_default=external_object_id_seq.next_value(),
                primary_key=True)
    """:obj:`int` : primary key"""

    type = Column(Enum(ExternalObjectType))
    """:obj:`ExternalObjectType` : the type of object"""

    links = relationship('ObjectLink',
                         back_populates='external_object',
                         cascade='all, delete-orphan')
    """list of :obj:`ObjectLink` : Links to where the object should be found"""

    values = relationship('Value',
                          back_populates='external_object',
                          cascade='all, delete-orphan')
    """list of :obj:`.value.Value` : arbitrary attributes for this object"""

    @declared_attr
    def attributes(cls):
        from .views import AttributesView
        return relationship(AttributesView,
                            primaryjoin=(foreign(AttributesView.external_object_id) == cls.id),
                            viewonly=True,
                            uselist=False)
    """:obj:`.views.AttributesView` : a computed list of attributes"""

    links_count = column_property(
        select([func.count('platform_id')]).
        select_from(table('object_link')).
        where(column('external_object_id') == id),
        deferred=True
    )

    @property
    def related_object(self):
        """Get the related object for additional metadatas if exists.

        Returns
        -------
        :obj:`None`
            if no class was mapped for this type
        :obj:`ExternalObjectMetaMixin`
            the mapped object linked with this type

        """
        cls = dict.get(external_object_meta_map, self.type, None)
        if cls is None:
            return None

        return cls.from_external_object(external_object=self)

    @property
    def episodes(self):
        return object_session(self).query(Episode).filter(Episode.series == self).\
            options(joinedload('external_object')).\
            order_by(Episode.season, Episode.episode).\
            limit(10)

    def add_meta(self, key, content):
        """Add a metadata on the related_object.

        Parameters
        ----------
        key : str
            the key of the metadata to insert
        content : any
            the content of the metadata to insert

        Raises
        ------
        matcher.exceptions.InvalidMetadata
            when the given metadata type can't be inserted
        matcher.exceptions.InvalidMetadataValue
            when the given metadata value can't be inserted

        """
        related_object = self.related_object
        if related_object is None:
            raise InvalidMetadata(self.type, key)

        related_object.add_meta(key, content)

    def add_attribute(self, attribute, platform):
        """Add an attribute to the object.

        Parameters
        ----------
        attribute : dict
            with a `type`, a `text` and maybe a `score_factor` item
        platform : Platform
            where this attribute was found

        """
        from .value import Value, ValueSource
        text = str(attribute['text']).strip()
        type = attribute['type']
        if not isinstance(type, ValueType):
            type = ValueType.from_name(type)
        if type is None:
            raise UnknownAttribute(attribute['type'])

        if 'score_factor' in attribute:
            score_factor = attribute['score_factor'] * 100
        else:
            score_factor = 100

        # Looking for an existing attribute
        # This loads *all* the attributes
        value = None
        for attr in self.values:
            if (type, text) == (attr.type, attr.text):
                value = attr
                break

        if value is None:
            # Create attribute value if it wasn't found
            value = Value(type=type, text=text)
            self.values.append(value)

        existing = next((source for source in value.sources
                         if source.platform == platform), None)
        if existing is None:
            existing = ValueSource(platform=platform)
            value.sources.append(existing)

        existing.score_factor = score_factor

    @staticmethod
    def lookup_from_links(links):
        """Lookup for an object from its links.

        Parameters
        ----------
        links : :obj:`list` of :obj:`tuple` of :obj:`int`
            list of links (platform, external_id) to use for lookup

        Returns
        -------
        :obj:`ExternalObject`
            the ExternalObject found using the links
        :obj:`None`
            if no ExternalObject was found

        """
        # Existing links from DB
        db_links = db.session.query(ObjectLink)\
            .filter(tuple_(ObjectLink.platform_id,
                           ObjectLink.external_id).in_(links))\
            .all()

        if len(db_links) == 0:
            return None
        else:
            # Check if they all link to the same object.
            # We may want to merge afterwards if they don't match
            objects = set(map(attrgetter('external_object'), db_links))

            # A set of those IDs should have a length of one
            # because there is only one distinct value in the array
            if len(objects) != 1:
                raise AmbiguousLinkError(objects)

            # Fetch the linked object
            return db_links[0].external_object

    def add_missing_links(self, links):
        """Add missing links to an external object.

        Parameters
        ----------
        links : :obj:`list` of :obj:`tuple` of :obj:`int`
            list of links to use, see :func:`lookup_from_links`

        Raises
        ------
        matcher.exceptions.ExternalIDMismatchError
            when there is two links on the same platform with different IDs

        """
        for (platform_id, external_id) in links:
            # Lookup for an existing link
            existing_link = next((link for link in self.links if
                                  link.platform_id == platform_id), None)
            if existing_link is None:
                # and create a new link if none found
                self.links.append(ObjectLink(external_object=self,
                                             platform_id=platform_id,
                                             external_id=external_id))

            elif existing_link.external_id != external_id:
                # Duplicate link with different ID for object
                raise ExternalIDMismatchError(existing_link, external_id)

    @staticmethod
    def lookup_or_create(obj_type, links, session):
        """Lookup for an object from its links.

        Parameters
        ----------
        obj_type : ExternalObjectType
            the type of object to search for.
        links : :obj:`list` of :obj:`tuple` of :obj:`int`
            list of links to use, see :func:`lookup_from_links`

        Notes
        -----
        If no object matches any of the links, it will be created.
        Non-existent links will be added to the object.

        """
        with lookup_lock, session.begin_nested():
            try:
                external_object = ExternalObject.lookup_from_links(links)
            except AmbiguousLinkError as err:
                external_object = err.resolve(session)

            if external_object is None:
                # There's no existing links, we shall create a new object
                external_object = ExternalObject(type=obj_type)
                session.add(external_object)

            # Check of obj_type matches
            if external_object.type is not obj_type and obj_type is not None:
                raise ObjectTypeMismatchError(external_object.type, obj_type)

            # Let's create the missing links
            external_object.add_missing_links(links)

        # We've added the links, we can safely return the external_object
        return external_object

    def merge(self, their):
        """Try to merge two objects.

        Parameters
        ----------
        their : ExternalObject
            the other object in which this object will be merged into

        Raises
        ------
        matcher.exceptions.ObjectTypeMismatchError
            when this object and their aren't the same type
        matcher.exceptions.LinksOverlap
            when the two objects have linked platforms in common

        """
        from .value import ValueSource
        # FIXME: A lot of other references needs merging (!)
        # First check if the merge is possible

        session = object_session(self)

        if self.type is not their.type:
            raise ObjectTypeMismatchError(is_type=self.type,
                                          should_be=their.type)

        to_delete = []
        for our_link in self.links:
            same_links = [link for link in their.links
                          if link.platform == our_link.platform and
                          our_link.external_id == link.external_id]
            to_delete += same_links

            if our_link.platform.allow_links_overlap:
                continue

            overlapping_links = [link for link in their.links
                                 if link.platform == our_link.platform and
                                 our_link.external_id != link.external_id]
            if overlapping_links:
                raise LinksOverlap(self, their)

        for d in to_delete:
            session.delete(d)

        # First merge the links
        for link in list(self.links):
            link.external_object_id = their.id
            session.add(link)

        session.commit()

        # Then merge the attributes
        for our_attr in self.values:
            # Lookup for a matching attribute
            their_attr = next((attr for attr in their.values
                               if our_attr.text == attr.text and
                               our_attr.type == attr.type), None)

            if their_attr is None:
                # Move attribute if it was not present on their side
                our_attr.external_object = their
                session.add(our_attr)
            else:
                # Else move only the value sources.
                # FIXME: *In theory*, we should not have any trouble merging by
                # moving because the platforms on their side are *in theory*
                # not the same as ours.
                # We might wanna check for this.
                for our_source in list(our_attr.sources):
                    session.merge(ValueSource(score_factor=our_source.score_factor,
                                              platform_id=our_source.platform_id,
                                              value_id=their_attr.id))

        for role in list(session.query(Role).filter(Role.external_object == self)):
            role.external_object = their

        for episode in list(session.query(Episode).filter(Episode.external_object == self)):
            if session.query(Episode).filter(Episode.external_object_id == their.id).first() is not None:
                session.delete(episode)
            else:
                episode.external_object = their

        for episode in list(session.query(Episode).filter(Episode.series == self)):
            episode.series = their

    def merge_and_delete(self, their, session):
        """Merge into another ExternalObject, and delete the old one.

        Parameters
        ----------
        their : ExternalObject
            the other object in which this object will be merged into
        session : sqlalchemy.orm.session.Session
            the session in which the deletion of the object will be done

        Returns
        -------
        :obj:`ExternalObject`
            the merged object

        """
        self.merge(their)
        session.delete(self)
        return their

    @classmethod
    def match_objects(cls, objects):
        from concurrent.futures import ThreadPoolExecutor
        from .. import app

        def execute(obj):
            with app.app_context():
                return obj.similar()

        # FIXME: max workers
        with ThreadPoolExecutor(max_workers=8) as executor:
            it = tqdm(executor.map(execute, objects), total=len(objects))
            for similar in it:
                s = list(similar)
                for (obj, into, score) in s:
                    it.write("{}\t{}\t{}".format(obj, into, score))

        # candidates = sorted(candidates, key=attrgetter('score'), reverse=True)

        # for candidate in candidates:
        #     print('{score:6.2f}: {obj:6d} -> {into:6d}'
        #           .format(**candidate._asdict()))

    @classmethod
    def merge_candidates(cls, candidates):
        merged = set()
        excluded = set()

        it = tqdm(candidates)
        for candidate in it:
            if candidate.obj in merged or candidate.into in excluded:
                continue

            src = db.session.query(cls).get(candidate.obj)
            dest = db.session.query(cls).get(candidate.into)

            # TODO: merge chains?
            if src is None:
                merged.add(candidate.obj)
                continue

            if dest is None:
                merged.add(candidate.into)
                continue

            try:
                src.merge_and_delete(dest, db.session)
                db.session.commit()
                it.write('Merged {} into {}'.format(src, dest))
            except Exception as e:
                it.write(repr(e))

    def similar(self):
        """Find similar objects.

        Returns
        -------
        list of :obj:`ExternalObject`
            other objects that are similar to this one

        """
        from .value import Value

        session = object_session(self)

        # FIXME: use other_value aliased name instead of value_1
        session.execute('SELECT set_limit(0.6)')
        other_value = aliased(Value)
        matches = session.query(
            other_value.external_object_id,
            func.sum(func.similarity(Value.text, other_value.text))
        )\
            .join(Value, and_(
                Value.type == ValueType.TITLE,
                Value.external_object == self,
                Value.text % other_value.text,
            ))\
            .join(other_value.external_object)\
            .filter(ExternalObject.type == self.type)\
            .filter(other_value.type == ValueType.TITLE)\
            .group_by(other_value.external_object_id)

        def links_overlap(a, b):
            platforms = set([l.platform for l in a]) & set([l.platform for l in b])
            return [p for p in platforms if p.type != PlatformType.GLOBAL and not p.allow_links_overlap]

        objects = [
            MergeCandidate(obj=self.id,
                           into=v[0],
                           score=v[1])
            for v in matches if not links_overlap(
                session.query(ObjectLink).filter(ObjectLink.external_object_id == v[0]),
                self.links
            )
        ]

        def into_year(text):
            m = re.search(r'(\d{4})', text)
            return int(m.group(1)) if m else None

        def into_float(i):
            try:
                return float(i)
            except ValueError:
                return None

        def numeric_attr(mine, their, type, process=into_float):
            my_attrs = set([process(attr.text) for attr in mine.values
                            if attr.type == type])
            their_attrs = set([process(attr.text) for attr in their.values
                               if attr.type == type])

            return len([True
                        for x in my_attrs
                        for y in their_attrs
                        if x is not None and
                        y is not None and
                        abs(x - y) < 1])

        def text_attr(mine, their, type, process=lambda n: n.lower()):
            my_attrs = set([process(attr.text) for attr in mine.values
                            if attr.type == type])
            their_attrs = set([process(attr.text) for attr in their.values
                               if attr.type == type])

            return len([True
                        for x in my_attrs
                        for y in their_attrs
                        if x is not None and
                        y is not None and
                        unidecode(x).lower() == unidecode(y).lower()])

        criterias = [
            lambda self, their: numeric_attr(self, their,
                                             ValueType.DATE, into_year),
            lambda self, their: numeric_attr(self, their,
                                             ValueType.DURATION, into_float),
            lambda self, their: text_attr(self, their, ValueType.COUNTRY),
            lambda self, their: text_attr(self, their, ValueType.TITLE),
        ]

        for candidate in objects:
            if candidate.obj == candidate.into:
                continue

            factor = 1
            their = session.query(ExternalObject).get(candidate.into)
            for criteria in criterias:
                factor *= math.pow(2, math.log2(1 + criteria(self, their)))
            yield MergeCandidate(obj=candidate.obj,
                                 into=candidate.into,
                                 score=candidate.score * factor)

    @staticmethod
    def insert_dict(data, scrap):
        """Insert a dict of raw data into the database.

        Parameters
        ----------
        data : dict
        scrap : Scrap
            the objects inserted will be added to this scrap

        Returns
        -------
        ExternalObject
            the top level inserted object

        """
        session = db.session
        obj = ExternalObject.lookup_or_create(
            obj_type=data['type'],
            links=data['links'],
            session=session,
        )

        for key, value in data['meta'].items():
            if value is not None:
                obj.add_meta(key, value)

        # We need to save the object first to reload the links
        session.add(obj)
        session.commit()

        # This checks if we explicitly scrapped the given object by giving
        # attributes
        # FIXME: maybe have this explicitly set in the input dict
        has_attributes = False

        if data['attributes'] is not None:
            with attributes_lock, session.begin_nested():
                for attribute in data['attributes']:
                    has_attributes = True
                    try:
                        obj.add_attribute(attribute, scrap.platform)
                    except UnknownAttribute as e:
                        # FIXME: do something with this exception
                        print(e)

        if has_attributes:
            # Find the link created for this platform and add the scrap to it
            with links_lock, session.begin_nested():
                link = session.query(ObjectLink).filter(ObjectLink.external_object == obj,
                                                        ObjectLink.platform == scrap.platform).first()
                if link is not None:
                    link.scraps.append(scrap)
                else:
                    raise LinkNotFound(links=obj.links, platform=scrap.platform)

        # Chech for related objects
        if data['related'] is not None:
            for child in data['related']:
                # Insert them…
                child_obj = ExternalObject.insert_dict(child, scrap)

                # …and if a relationship is specified, use a map to bind the
                # two objects together
                if 'relation' in child:
                    create_relationship(child['relation'], obj, child_obj)

        session.commit()

        return obj

    @staticmethod
    def normalize_dict(raw):
        """Normalize a dict from a request payload.

        Parameters
        ----------
        raw : dict
            the raw input from the requests JSON

        Returns
        -------
        dict
            the normalized dict that can be passed to :func:`insert_dict`

        Todo
        ----
        Document the shape of the raw and normalized dicts

        """
        # TODO: Error handling

        # FIXME: move those utils

        # TODO: move to a real python object?
        # FIXME: how do i comment this?
        data = {
            # ExternalObjectType
            'type': None,

            # Array<{'type': string, 'text': str, 'score_factor': float}>
            'attributes': None,

            # Array<(int, str)>
            'links': None,

            # Array<self>
            'related': None,

            # str
            'relation': None,

            # dict<str, any>
            'meta': {}
        }

        if 'type' in raw and raw['type'] is not None:
            # 'SERIES' was once named 'SERIE'
            if raw['type'].lower() == 'serie':
                raw['type'] = 'series'

            data['type'] = ExternalObjectType.from_name(raw['type'])

        if 'attributes' in raw and raw['attributes'] is not None:
            data['attributes'] = list(itertools.chain.from_iterable(
                [_normalize_attribute(t, a)
                 for t, a in raw['attributes'].items()]))
            data['attributes'] = deduplicate(data['attributes'],
                                             itemgetter('text'))

        if 'links' in raw and raw['links'] is not None:
            data['links'] = list(map(_normalize_link, raw['links']))

        if 'related' in raw and raw['related'] is not None:
            data['related'] = list(map(ExternalObject.normalize_dict,
                                       raw['related']))

        if 'relation' in raw and raw['relation'] is not None:
            data['relation'] = str(raw['relation'])

        if 'meta' in raw and raw['meta'] is not None:
            data['meta'] = raw['meta']

        return data

    def __repr__(self):
        return '<ExternalObject {} {}>'.format(self.id, self.type)


class ObjectLink(Base):
    """Links an object to a platform, with it's ID on the platform."""

    __tablename__ = 'object_link'

    object_link_id_seq = Sequence('object_link_id_seq', metadata=Base.metadata)
    id = Column(Integer,
                object_link_id_seq,
                server_default=object_link_id_seq.next_value(),
                primary_key=True)
    """:obj:`int` : primary key"""

    external_object_id = Column(Integer,
                                ForeignKey('external_object.id'),
                                nullable=False)
    """:obj:`int` : Foreign key to the linked object"""

    platform_id = Column(Integer,
                         ForeignKey('platform.id'),
                         nullable=False)
    """:obj:`int` : Foreign key to the linked platform"""

    external_id = Column(Text)
    """:obj:`str` : ID of the external_object on the platform"""

    external_object = relationship('ExternalObject',
                                   back_populates='links')
    """:obj:`ExternalObject` : Relationship to the linked object"""

    platform = relationship('Platform',
                            back_populates='links')
    """:obj:`.platform.Platform` : Relationship to the linked platform"""

    scraps = relationship('Scrap',
                          secondary='scrap_link',
                          back_populates='links')
    """list of :obj:`Scrap` : scraps where the link was found"""

    imports = relationship('ImportFile',
                           secondary='import_link',
                           back_populates='links')

    @property
    def url(self):
        format = self.platform.url.get(str(self.external_object.type), None)
        return None if format is None else format.format(self.external_id)

    def __repr__(self):
        return '<ObjectLink ({}, {})>'.format(self.external_object,
                                              self.platform)


class Role(Base):
    """A role of a person on another object (movie/episode/series…)."""

    __tablename__ = 'role'

    # FIXME: how to represent multiple roles of a person on the same object?
    __table_args__ = (
        PrimaryKeyConstraint('person_id', 'external_object_id'),
    )

    person_id = Column(Integer,
                       ForeignKey('external_object.id'))
    """:obj:`int` : The ID of the person concerned"""
    external_object_id = Column(Integer,
                                ForeignKey('external_object.id'))
    """:obj:`int` : The ID of the object concerned"""

    person = relationship('ExternalObject',
                          foreign_keys=[person_id])
    """:obj:`ExternalObject` : The person concerned"""

    external_object = relationship('ExternalObject',
                                   foreign_keys=[external_object_id])
    """:obj:`ExternalObject` : The object concerned"""

    role = Column(Enum(RoleType))
    """:obj:`RoleType` : The type of role"""


class ExternalObjectMetaMixin(object):
    """Mixin to add metadatas to specific ExternalObject types.

    Attributes
    ----------
    external_object_id : :obj:`int`
        The foreign key of the linked object
    external_object : :obj:`ExternalObject`
        The linked object

    """

    object_type = None
    """The type of ExternalObject this object maps to"""

    @declared_attr
    def external_object_id(cls):
        """Get the type of the external_object_id attribute."""
        return Column(Integer,
                      ForeignKey('external_object.id',
                                 onupdate='CASCADE',
                                 ondelete='CASCADE'),
                      primary_key=True)

    @declared_attr
    def external_object(cls):
        """Get the type of the external_object attribute."""
        return relationship('ExternalObject',
                            foreign_keys=[cls.external_object_id])

    @classmethod
    def from_external_object(cls, external_object):
        """Get the corresponding object for a given ExternalObject.

        Parameters
        ----------
        external_object : ExternalObject
            from which import we want to get the metadatas

        Returns
        -------
        cls

        Notes
        -----
        The metadata object is created and added to the session if non-existent

        """
        return db.session.merge(cls(external_object_id=external_object.id))

    @classmethod
    def register(cls):
        """Register the class to the external_object_meta_map."""
        if cls.object_type is None:
            raise Exception("object_type isn't defined for {!r}"
                            .format(cls))

        if cls.object_type in external_object_meta_map:
            raise Exception(
                "ExternalObjectMetaMixin was already registered for {!r}"
                .format(cls.object_type)
            )

        external_object_meta_map[cls.object_type] = cls

    def add_meta(self, key, content):
        """Add a metadata to the object.

        Parameters
        ----------
        key : str
        content : any

        Raises
        ------
        matcher.exceptions.InvalidMetadata

        """
        raise InvalidMetadata(self.object_type, key)


class Episode(Base, ExternalObjectMetaMixin):
    """An episode of a TV series."""

    __tablename__ = 'episode'
    object_type = ExternalObjectType.EPISODE

    series_id = Column(Integer,
                       ForeignKey('external_object.id',
                                  ondelete='CASCADE',
                                  onupdate='CASCADE'))

    # FIXME: how to handle special episodes?
    episode = Column(Integer)
    """:obj:`int` : The episode number in the season"""

    season = Column(Integer)
    """:obj:`int` : The season number in the series"""

    series = relationship('ExternalObject',
                          foreign_keys=[series_id])
    """:obj:`ExternalObject` : The series in which this episode is in"""

    def set_parent(self, parent):
        """Set the parent season.

        Parameters
        ----------
        parent : ExternalObject
            the season that contains this :obj:`Episode`

        Raises
        ------
        matcher.exceptions.InvalidRelation
            when the parent's type isn't a :obj:`ExternalObjectType.SERIES`

        """
        if parent.type != ExternalObjectType.SERIES:
            raise InvalidRelation("part of", parent, self)
        self.series = parent

    def add_meta(self, key, content):
        """Add a metadata to the object.

        See :func:`ExternalObjectMetaMixin.add_meta`

        """

        try:
            if key == "episode":
                self.episode = int(content)
            elif key == "season":
                self.season = int(content)
            else:
                raise InvalidMetadata(ExternalObjectType.EPISODE, key)
        except ValueError:
            raise InvalidMetadataValue(key, content)


class Person(Base, ExternalObjectMetaMixin):
    """Represents a person."""

    __tablename__ = 'person'
    object_type = ExternalObjectType.PERSON

    gender = Column(Enum(Gender, name='gender'),
                    nullable=False,
                    default=Gender.NOT_KNOWN)
    """:obj:`Gender` : The gender of the person"""

    def add_role(self, movie, role):
        """Add a role to a person.

        Raises
        ------
        NotImplementedError
            Not implemented

        """
        with role_lock, db.session.begin_nested():
            if db.session.query(Role).filter(Role.person == self.external_object and
                                             Role.external_object == movie).first() is None:
                db.session.merge(Role(person=self.external_object,
                                      external_object=movie,
                                      role=role))

    def add_meta(self, key, content):
        """Add a metadata to the object.

        See :func:`ExternalObjectMetaMixin.add_meta`

        """
        if key != "gender":
            raise InvalidMetadata(self.object_type, key)

        gender = Gender.from_name(content)
        if gender is None:
            raise InvalidMetadataValue(key, content)


Episode.register()
Person.register()
