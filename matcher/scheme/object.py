import itertools
from operator import attrgetter, itemgetter
from sqlalchemy import tuple_, func
from sqlalchemy.ext.declarative import declared_attr
from sqlalchemy.orm.exc import NoResultFound

from ..app import db
from ..exceptions import AmbiguousLinkError, ExternalIDMismatchError, \
    ObjectTypeMismatchError, UnknownAttribute, LinkNotFound
from .mixins import ResourceMixin
from .utils import CustomEnum
from .platform import Platform
from .value import ValueType, Value, ValueSource


class ExternalObjectType(CustomEnum):
    """A type of object in database"""

    PERSON = 1
    """Represents a person. Can be an actor, director, or anything else"""

    MOVIE = 2
    """Represents a single movie"""

    EPISODE = 3
    """Represents an episode of a serie's season"""

    SEASON = 4
    """Represents a season of a serie"""

    SERIE = 5
    """Represents a (TV) serie"""


scrap_link = db.Table(
    'scrap_link',
    db.Column('scrap_id',
              db.ForeignKey('scrap.id'),
              primary_key=True),
    db.Column('object_link_id',
              db.ForeignKey('object_link.id'),
              primary_key=True),
)


class ExternalObject(db.Model, ResourceMixin):
    """An object imported from scraping"""

    __tablename__ = 'external_object'

    id = db.Column(db.Integer,
                   db.Sequence('external_object_id_seq'),
                   primary_key=True)

    type = db.Column(db.Enum(ExternalObjectType))

    links = db.relationship('ObjectLink',
                            back_populates='external_object')
    """Links to where the object has been/should be found"""

    attributes = db.relationship('Value',
                                 back_populates='external_object',
                                 cascade='all, delete-orphan')
    """A list of arbitrary attributes associated with this object"""

    @property
    def related_object(self):
        """The related object for additional metadatas if exists"""

        # TODO: make this map more generic
        class_map = {
            ExternalObjectType.PERSON: Person,
            ExternalObjectType.EPISODE: Episode,
            ExternalObjectType.SEASON: Season,
            ExternalObjectType.MOVIE: None,
            ExternalObjectType.SERIE: None,
        }

        cls = dict.get(class_map, self.type, None)
        if cls is None:
            return None

        return cls.from_external_object(external_object=self)

    def add_attribute(self, attribute, platform):
        """Add an attribute to the object"""

        text = str(attribute['text'])
        type = attribute['type']
        if not isinstance(type, ValueType):
            type = ValueType.from_name(type)
        if type is None:
            raise UnknownAttribute(attribute['type'])

        if 'score_factor' in attribute:
            score_factor = attribute['score_factor']
        else:
            score_factor = 100

        # Looking for an existing attribute
        # This loads *all* the attributes
        value = None
        for attr in self.attributes:
            if (type, text) == (attr.type, attr.text):
                value = attr
                break

        if value is None:
            # Create attribute value if it wasn't found
            value = Value(type=type, text=text)
            self.attributes.append(value)

        if not any(source.platform == platform for source in value.sources):
            value.sources.append(ValueSource(
                platform=platform, score_factor=score_factor))

    def lookup_from_links(links):
        """Lookup for an object from its links

        :links: List of links (platform, external_id) to use.
        """

        # Existing links from DB
        db_links = ObjectLink.query\
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
        """Add missing links to an external object"""

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

    def lookup_or_create(obj_type, links, session=None):
        """Lookup for an object from its links

        :obj_type: The type of object to search for.
                   Throws an exception if type mismatches.
        :links: List of links to use
                Non-existent links will be created
        """

        try:
            external_object = ExternalObject.lookup_from_links(links)
        except AmbiguousLinkError as err:
            if session is None:
                # FIXME: custom exception
                raise Exception('Can\'t merge without session')
            else:
                external_object = err.resolve(session)
                # We need to commit before continuing
                # FIXME: do we?
                session.commit()

        if external_object is None:
            # There's no existing links, we shall create a new object
            external_object = ExternalObject(type=obj_type)

        # Check of obj_type matches
        if external_object.type is not obj_type:
            raise ObjectTypeMismatchError(external_object.type, obj_type)

        # Let's create the missing links
        external_object.add_missing_links(links)

        # We've added the links, we can safely return the external_object
        return external_object

    def merge(self, their):
        """Try to merge two objects"""
        # FIXME: A lot of other references needs merging (!)
        # First check if the merge is possible

        if self.type is not their.type:
            raise ObjectTypeMismatchError(is_type=self.type,
                                          should_be=their.type)

        our_platforms = set(map(attrgetter('platform'), self.links))
        their_platforms = set(map(attrgetter('platform'), their.links))

        # The two objects should not have links to the same platform
        if our_platforms & their_platforms:
            # FIXME: custom exception
            raise Exception("Cannot merge")

        # First merge the links
        for link in list(self.links):
            link.external_object = their

        # Then merge the attributes
        for our_attr in self.attributes:
            # Lookup for a matching attribute
            their_attr = next((attr for attr in their.attributes
                               if our_attr.text == attr.text
                               and our_attr.type == attr.type), None)

            if their_attr is None:
                # Move attribute if it was not present on their side
                our_attr.external_object = their
                # their.attributes.append(our_attr)
            else:
                # Else move only the value sources.
                # FIXME: *In theory*, we should not have any trouble merging by
                # moving because the platforms on their side are *in theory*
                # not the same as ours.
                # We might wanna check for this.
                for our_source in our_attr.sources:
                    our_source.value = their_attr
                    # their_attr.sources.append(our_source)

    def merge_and_delete(self, their, session):
        """Merge into another ExternalObject, and delete the old one"""
        self.merge(their)
        session.delete(self)
        return their

    def similar(self):
        """Find similar objects"""

        titles = sorted(filter(lambda a: a.type == ValueType.TITLE,
                               self.attributes),
                        key=attrgetter('score'),
                        reverse=True)

        objects = []
        for title in titles:
            values = Value.query\
                .filter(Value.type == ValueType.TITLE)\
                .filter(func.lower(Value.text) == func.lower(title.text))\
                .filter(Value.external_object != self)
            objects += list(map(lambda v: (v.score * title.score,
                                           v.external_object), values))

        return map(itemgetter(1), sorted(objects, key=itemgetter(0)))

    def insert_dict(data, scrap):
        obj = ExternalObject.lookup_or_create(
            obj_type=data['type'],
            links=data['links'],
            session=db.session,
        )

        # This checks if we explicitly scrapped the given object by giving
        # attributes
        # FIXME: maybe have this explicitly set in the input dict
        has_attributes = False

        if data['attributes'] is not None:
            for attribute in data['attributes']:
                has_attributes = True
                try:
                    obj.add_attribute(attribute, scrap.platform)
                except UnknownAttribute as e:
                    # FIXME: do something with this exception
                    print(e)

        # We need to save the object first to reload the links
        db.session.add(obj)
        db.session.commit()

        if has_attributes:
            # Find the link created for this platform and add the scrap to it
            link = next((link for link in obj.links
                         if link.platform == scrap.platform), None)
            if link is not None:
                link.scraps.append(scrap)
            else:
                raise LinkNotFound(links=obj.links, platform=scrap.platform)
            db.session.commit()

        return obj

    def normalize_dict(raw):
        """Normalize a dict from a request payload"""

        # TODO: Error handling

        # FIXME: move those utils
        def normalize_attribute(type, values):
            if not isinstance(values, list):
                values = [values]
            return [{'type': type, **attr} for attr in values]

        def normalize_relation(relation):
            if 'type' not in relation:
                relation = {'type': relation}
            return relation

        def normalize_link(link):
            """Map a link to a (platform, external_id) tuple"""
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
            platform = Platform.lookup(platform)
            if platform is None:
                # TODO: custom exception
                raise Exception('platform not found')
            else:
                platform_id = platform.id

            return (int(platform_id), str(external_id))

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
            'relation': None
        }

        if 'type' in raw and raw['type'] is not None:
            data['type'] = ExternalObjectType.from_name(raw['type'])

        if 'attributes' in raw and raw['attributes'] is not None:
            data['attributes'] = list(itertools.chain.from_iterable(
                [normalize_attribute(t, a)
                 for t, a in raw['attributes'].items()]))

        if 'links' in raw and raw['links'] is not None:
            data['links'] = list(map(normalize_link, raw['links']))

        if 'related' in raw and raw['related'] is not None:
            data['related'] = list(map(ExternalObject.normalize_dict,
                                       raw['related']))

        if 'relation' in raw and raw['relation'] is not None:
            data['relation'] = normalize_relation(raw['relation'])

        return data

    def __repr__(self):
        return '<ExternalObject {} {}>'.format(self.id, self.type)


class ObjectLink(db.Model):
    """Links an object to a platform, with it's ID on the platform"""

    __tablename__ = 'object_link'

    id = db.Column(db.Integer,
                   db.Sequence('object_link_id_seq'),
                   primary_key=True)

    external_object_id = db.Column(db.Integer,
                                   db.ForeignKey('external_object.id'),
                                   nullable=False)
    platform_id = db.Column(db.Integer,
                            db.ForeignKey('platform.id'),
                            nullable=False)
    external_id = db.Column(db.String)
    """The ID of the object on the platform(i.e. IMDb ID)"""

    external_object = db.relationship('ExternalObject',
                                      back_populates='links')
    """The object linked"""

    platform = db.relationship('Platform',
                               back_populates='links')
    """The platform linked"""

    scraps = db.relationship('Scrap',
                             secondary='scrap_link',
                             back_populates='links')
    """Lists of scraps where the link was(or should be) found"""

    # FIXME: do something more generic?
    work_meta = db.relationship('ObjectLinkWorkMeta')
    """Some metadata associated with the item on the platform"""

    def __repr__(self):
        return '<ObjectLink ({}, {})>'.format(self.external_object,
                                              self.platform)


class ObjectLinkWorkMeta(db.Model):
    """Metadatas associated with an object on a platform"""

    __tablename__ = 'object_link_work_meta'

    id = db.Column(db.Integer,
                   db.ForeignKey('object_link.id'),
                   nullable=False,
                   primary_key=True)

    original_content = db.Column(db.Boolean)
    """Is this object produced by the platform?"""

    rating = db.Column(db.Integer)
    """What's the rating of this item on the platform"""

    link = db.relationship('ObjectLink',
                           back_populates='work_meta',
                           uselist=False)
    """The link concerned by those metadatas"""

    def __repr__(self):
        return '<ObjectLinkWorkMeta {}>'.format(self.link)


class ExternalObjectMeta(object):
    """Mixin to add metadatas to specific ExternalObject types"""

    @declared_attr
    def external_object_id(cls):
        return db.Column(db.Integer,
                         db.ForeignKey('external_object.id'),
                         primary_key=True)
    """The foreign key in the table"""

    @declared_attr
    def external_object(cls):
        return db.relationship('ExternalObject',
                               foreign_keys=[cls.external_object_id])
    """The actual relationship"""

    @classmethod
    def from_external_object(cls, external_object):
        """Get the corresponding object for a given ExternalObject"""
        try:
            obj = cls.query\
                .filter(cls.external_object == external_object)\
                .one()
        except NoResultFound:
            obj = cls(external_object=external_object)
            db.session.add(obj)

        return obj


class Episode(db.Model, ExternalObjectMeta):
    """An episode of a TV serie"""

    __tablename__ = 'episode'

    season_id = db.Column(db.Integer,
                          db.ForeignKey('external_object.id'))

    # FIXME: how to handle special episodes?
    number = db.Column(db.Integer)
    """The episode number in the season"""

    season = db.relationship('ExternalObject',
                             foreign_keys=[season_id])
    """The season in which this episode is in"""


class Season(db.Model, ExternalObjectMeta):
    """A season of a TV serie"""

    __tablename__ = 'season'

    serie_id = db.Column(db.Integer,
                         db.ForeignKey('external_object.id'))

    # FIXME: how to handle special episodes/seasons?
    number = db.Column(db.Integer)
    """The season number"""

    serie = db.relationship('ExternalObject',
                            foreign_keys=[serie_id])
    """The object representing the serie in which this episode is"""


class Gender(CustomEnum):
    """ISO/IEC 5218 compliant gender enum"""
    NOT_KNOWN = 0
    MALE = 1
    FEMALE = 2
    NOT_APPLICABLE = 9


class RoleType(CustomEnum):
    """A type of role of a person on another object"""
    DIRECTOR = 0
    ACTOR = 1
    WRITER = 2


class Role(db.Model):
    """A role of a person on another object (movie/episode/serie…)"""

    __tablename__ = 'role'

    # FIXME: how to represent multiple roles of a person on the same object?
    __table_args__ = (
        db.PrimaryKeyConstraint('person_id', 'external_object_id'),
    )

    person_id = db.Column(db.Integer,
                          db.ForeignKey('person.id'))
    external_object_id = db.Column(db.Integer,
                                   db.ForeignKey('external_object.id'))

    person = db.relationship('Person',
                             foreign_keys=[person_id],
                             back_populates='roles')
    """The person concerned"""

    external_object = db.relationship('ExternalObject',
                                      foreign_keys=[external_object_id])
    """The object concerned"""

    role = db.Column(db.Enum(RoleType))
    """The type of role"""


class Person(db.Model, ExternalObjectMeta):
    """Represents a person"""
    __tablename__ = 'person'

    id = db.Column(db.Integer,
                   db.Sequence('person_id_seq'),
                   primary_key=True)

    gender = db.Column(db.Enum(Gender, name='gender'),
                       nullable=False,
                       default=Gender.NOT_KNOWN)
    """The gender of the person"""

    roles = db.relationship('Role',
                            back_populates='person')
    """The roles this person has on various objects"""
