from .mixins import CustomEnum, ResourceMixin
from .platform import Platform
from .value import ValueType, Value, ValueSource
from matcher import db
from sqlalchemy import tuple_


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


# TODO: move those exceptions somewhere else
class AmbiguousLinkError(Exception):
    """Raise when the lookup ends up returning multiple object"""


class ObjectTypeMismatchError(Exception):
    """Raise when the object found isn't the same type as it should"""


class ExternalIDMismatchError(Exception):
    """Raise when two links IDs for the same object/platform mismatch"""


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
                                 back_populates='external_object')
    """A list of arbitrary attributes associated with this object"""

    def add_attributes(self, attributes, platform):
        """Add a list of attributes to the object"""
        for attribute in attributes:
            self.add_attribute(attribute, platform)

    def add_attribute(self, attribute, platform):
        """Add an attribute to the object"""

        text = str(attribute['text'])
        type = attribute['type']
        if not isinstance(type, ValueType):
            type = ValueType.from_name(type)
        if type is None:
            # FIXME: this should raise an exception
            print('type {} not defined'.format(attribute['type']))
            return

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

    def lookup_or_create(obj_type, links):
        """Lookup for an object from its links

        :obj_type: The type of object to search for.
                   Throws an exception if type mismatches.
        :links: List of links to use
                Non-existent links will be created
        """
        def map_links(link):
            """Maps link to a (platform, external_id) tuple"""
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

            return (platform_id, external_id)

        # Mapping links to a (platform_id, external_id) tuple
        mapped_links = list(map(map_links, links))

        # Existing links from DB
        object_links = ObjectLink.query\
            .filter(tuple_(ObjectLink.platform_id,
                           ObjectLink.external_id).in_(mapped_links))\
            .all()

        if len(object_links) == 0:
            # There's no existing links, we shall create a new object
            external_object = ExternalObject(type=obj_type)
        else:
            # Check if they all link to the same object.
            # We may want to merge afterwards if they don't match
            ids = map(lambda link: link.external_object_id, object_links)
            # A set of those IDs should have a length of one
            # because there is only one distinct value in the array
            equals = len(set(ids)) == 1

            if not equals:
                # TODO: save the ids in the exception for merging
                raise AmbiguousLinkError(
                    'existing links do not link to the same object')

            # Fetch the linked object
            external_object = object_links[0].external_object

        # Check of obj_type matches
        if external_object.type is not obj_type:
            raise ObjectTypeMismatchError(
                'is {}, should be {}'.format(external_object.type, obj_type))

        # Let's create the missing links
        for (platform_id, external_id) in mapped_links:
            # Lookup for an existing link
            existing_link = next((link for link in external_object.links if
                                  link.platform_id == platform_id), None)
            if existing_link is None:
                # and create a new link if none found
                external_object.links.append(
                    ObjectLink(external_object=external_object,
                               platform_id=platform_id,
                               external_id=external_id))

            elif existing_link.external_id != external_id:
                # Duplicate link with different ID for object
                raise ExternalIDMismatchError(
                    'link on {} has ID {}, should be {}'.format(
                        existing_link.platform.slug,
                        existing_link.external_id,
                        external_id))

        # We've added the links, we can safely return the external_object
        return external_object

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


class Episode(db.Model):
    """An episode of a TV serie"""

    __tablename__ = 'episode'

    external_object_id = db.Column(db.Integer,
                                   db.ForeignKey('external_object.id'),
                                   primary_key=True)
    season_id = db.Column(db.Integer,
                          db.ForeignKey('external_object.id'))

    # FIXME: how to handle special episodes?
    number = db.Column(db.Integer)
    """The episode number in the season"""

    external_object = db.relationship('ExternalObject',
                                      foreign_keys=[external_object_id])
    """The object representing this episode"""

    season = db.relationship('ExternalObject',
                             foreign_keys=[season_id])
    """The season in which this episode is in"""


class Season(db.Model):
    """A season of a TV serie"""

    __tablename__ = 'season'

    external_object_id = db.Column(db.Integer,
                                   db.ForeignKey('external_object.id'),
                                   primary_key=True)
    serie_id = db.Column(db.Integer,
                         db.ForeignKey('external_object.id'))

    # FIXME: how to handle special episodes/seasons?
    number = db.Column(db.Integer)
    """The season number"""

    external_object = db.relationship('ExternalObject',
                                      foreign_keys=[external_object_id])
    """The object representing this season"""

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


class Person(db.Model):
    """Represents a person"""
    __tablename__ = 'person'

    id = db.Column(db.Integer,
                   db.Sequence('person_id_seq'),
                   primary_key=True)

    external_object_id = db.Column(db.Integer,
                                   db.ForeignKey('external_object.id'),
                                   nullable=False)
    external_object = db.relationship('ExternalObject',
                                      foreign_keys=[external_object_id])
    """The object linked to this person"""

    gender = db.Column(db.Enum(Gender, name='gender'),
                       nullable=False,
                       default=Gender.NOT_KNOWN)
    """The gender of the person"""

    roles = db.relationship('Role',
                            back_populates='person')
    """The roles this person has on various objects"""
