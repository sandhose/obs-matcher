import enum
from sqlalchemy.orm import object_session
from sqlalchemy.ext.hybrid import hybrid_property
from matcher import db


class ExternalObjectType(enum.Enum):
    AV_WORK = 1
    MOVIE = 2
    EPISODE = 3
    SEASON = 4
    SERIE = 5

    def model(self):
        from matcher.scheme.work import AVWork, Movie, Episode, Season, Serie

        if (self == ExternalObjectType.AV_WORK):
            return AVWork
        elif (self == ExternalObjectType.MOVIE):
            return Movie
        elif (self == ExternalObjectType.EPISODE):
            return Episode
        elif (self == ExternalObjectType.SEASON):
            return Season
        elif (self == ExternalObjectType.SERIE):
            return Serie


scrap_link = db.Table(
    'scrap_link',
    db.Column('scrap_id',
              db.ForeignKey('scrap.id'),
              primary_key=True),
    db.Column('object_link_id',
              db.ForeignKey('object_link.id'),
              primary_key=True),
)


class ExternalObject(db.Model):
    __tablename__ = 'external_object'

    id = db.Column(db.Integer,
                   db.Sequence('external_object_id_seq'),
                   primary_key=True)

    type = db.Column(db.Enum(ExternalObjectType, name='type'))

    links = db.relationship('ObjectLink',
                            back_populates='object')

    @property
    def linked_object(self):
        return object_session(self).\
               query(self.type.model()).\
               filter(self.type.model().external_object_id == self.id).\
               first()

    def __repr__(self):
        return '<ExternalObject {} {}>'.format(self.id, self.linked_object)


class ObjectLink(db.Model):
    __tablename__ = 'object_link'

    id = db.Column(db.Integer,
                   db.Sequence('object_link_id_seq'),
                   primary_key=True)

    object_id = db.Column(db.Integer,
                          db.ForeignKey('external_object.id'),
                          nullable=False)
    platform_id = db.Column(db.Integer,
                            db.ForeignKey('platform.id'),
                            nullable=False)
    external_id = db.Column(db.String)

    object = db.relationship('ExternalObject',
                             back_populates='links')
    platform = db.relationship('Platform',
                               back_populates='links')
    scraps = db.relationship('Scrap',
                             secondary='scrap_link',
                             back_populates='links')
    work_meta = db.relationship('ObjectLinkWorkMeta')

    def __repr__(self):
        return '<ObjectLink ({}, {})>'.format(self.object, self.platform)


class ObjectLinkWorkMeta(db.Model):
    __tablename__ = 'object_link_work_meta'

    id = db.Column(db.Integer,
                   db.ForeignKey('object_link.id'),
                   nullable=False,
                   primary_key=True)

    original_content = db.Column(db.Boolean)
    rating = db.Column(db.Integer)

    link = db.relationship('ObjectLink',
                           back_populates='work_meta',
                           uselist=False)

    def __repr__(self):
        return '<ObjectLinkWorkMeta {}>'.format(self.link)
