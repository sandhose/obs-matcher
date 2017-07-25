from .mixins import CustomEnum, ResourceMixin
from matcher import db


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
                                 back_populates='external_object')
    """A list of arbitrary attributes associated with this object"""

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
    """The ID of the object on the platform (i.e. IMDb ID)"""

    external_object = db.relationship('ExternalObject',
                                      back_populates='links')
    """The object linked"""

    platform = db.relationship('Platform',
                               back_populates='links')
    """The platform linked"""

    scraps = db.relationship('Scrap',
                             secondary='scrap_link',
                             back_populates='links')
    """Lists of scraps where the link was (or should be) found"""

    # FIXME: Do something more generic?
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

    # FIXME: How to represent multiple roles of a person on the same object?
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
