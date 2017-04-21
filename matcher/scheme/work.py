import enum

from matcher import db


class AvWorkType(enum.Enum):
    movie = 1
    serie = 2


class AvWork(db.Model):
    __tablename__ = 'av_work'

    id = db.Column(db.Integer, db.Sequence('av_work_id_seq'), primary_key=True)

    external_object_id = db.Column(db.Integer,
                                   db.ForeignKey('external_object.id'),
                                   nullable=False)
    title_value_id = db.Column(db.Integer, db.ForeignKey('value_id.id'),
                               nullable=False)
    date_value_id = db.Column(db.Integer, db.ForeignKey('value_id.id'),
                              nullable=False)
    duration_value_id = db.Column(db.Integer, db.ForeignKey('value_id.id'),
                                  nullable=False)

    external_object = db.relationship('ExternalObject',
                                      foreign_keys=[external_object_id])
    title = db.relationship('ValueID', foreign_keys=[title_value_id])
    date = db.relationship('ValueID', foreign_keys=[date_value_id])
    type = db.Column(db.Enum(AvWorkType, name='avwork_type'))
    duration = db.relationship('ValueID', foreign_keys=[duration_value_id])
    roles = db.relationship('Role', back_populates='av_work')


class Movie(db.Model):
    __tablename__ = 'movie'

    id = db.Column(db.Integer, db.Sequence('movie_id_seq'), primary_key=True)
    av_work_id = db.Column(db.Integer, db.ForeignKey(
        'av_work.id'), nullable=False)
    country_value_id = db.Column(db.Integer, db.ForeignKey('value_id.id'),
                                 nullable=False)
    genres_value_id = db.Column(db.Integer, db.ForeignKey('value_id.id'),
                                nullable=False)

    av_work = db.relationship('AvWork', foreign_keys=[av_work_id])
    country = db.relationship('ValueID', foreign_keys=[country_value_id])
    genres = db.relationship('ValueID', foreign_keys=[genres_value_id])


class Episode(db.Model):
    __tablename__ = 'episode'

    id = db.Column(db.Integer, db.Sequence('episode_id_seq'), primary_key=True)

    external_object_id = db.Column(db.Integer,
                                   db.ForeignKey('external_object.id'),
                                   nullable=False)
    season_id = db.Column(db.Integer, db.ForeignKey(
        'season.id'), nullable=False)

    external_object = db.relationship('ExternalObject',
                                      foreign_keys=[external_object_id])
    season = db.relationship('Season', foreign_keys=[season_id])
    number = db.Column(db.Integer, nullable=False)


class Season(db.Model):
    __tablename__ = 'season'

    id = db.Column(db.Integer, db.Sequence('season_id_seq'), primary_key=True)

    external_object_id = db.Column(db.Integer,
                                   db.ForeignKey('external_object.id'),
                                   nullable=False)
    serie_id = db.Column(db.Integer, db.ForeignKey('serie.id'), nullable=False)

    external_object = db.relationship('ExternalObject',
                                      foreign_keys=[external_object_id])
    serie = db.relationship('serie', foreign_keys=[serie_id])
    number = db.Column(db.Integer, nullable=False)


class Serie(db.Model):
    __tablename__ = 'serie'
    id = db.Column(db.Integer, db.Sequence('serie_id_seq'), primary_key=True)

    external_object_id = db.Column(db.Integer,
                                   db.ForeignKey('external_object.id'),
                                   nullable=False)
    title_value_id = db.Column(db.Integer, db.ForeignKey('value_id.id'),
                               nullable=False)
    country_value_id = db.Column(db.Integer, db.ForeignKey('value_id.id'),
                                 nullable=False)
    genres_value_id = db.Column(db.Integer, db.ForeignKey('value_id.id'),
                                nullable=False)

    external_object = db.relationship('ExternalObject',
                                      foreign_keys=[external_object_id])
    title = db.relationship('ValueID', foreign_keys=[title_value_id])
    country = db.relationship('ValueID', foreign_keys=[country_value_id])
    genres = db.relationship('ValueID', foreign_keys=[genres_value_id])
