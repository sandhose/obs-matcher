from matcher import db


class PlatformGroup(db.Model):
    __tablename__ = 'platform_group'

    id = db.Column(db.Integer,
                   db.Sequence('platform_group_id_seq'),
                   primary_key=True)
    name = db.Column(db.String,
                     nullable=False)

    platforms = db.relationship('Platform',
                                back_populates='group')


class Platform(db.Model):
    __tablename__ = 'platform'

    id = db.Column(db.Integer,
                   db.Sequence('platform_id_seq'),
                   primary_key=True)
    name = db.Column(db.String,
                     nullable=False)
    group_id = db.Column(db.Integer,
                         db.ForeignKey('platform_group.id'))
    url = db.Column(db.String)
    country = db.Column(db.String(2))
    max_rating = db.Column(db.Integer)
    base_score = db.Column(db.Integer,
                           nullable=False)

    group = db.relationship('PlatformGroup',
                            back_populates='platforms')
    scraps = db.relationship('Scrap',
                             back_populates='platform')
    values = db.relationship('Value',
                             secondary='value_source',
                             back_populates='sources')


class Scrap(db.Model):
    __tablename__ = 'scrap'

    id = db.Column(db.Integer,
                   db.Sequence('scrap_id_seq'),
                   primary_key=True)
    platform_id = db.Column(db.Integer,
                            db.ForeignKey('platform.id'),
                            nullable=False)
    date = db.Column(db.DateTime)

    platform = db.relationship('Platform',
                               back_populates='scraps')
    links = db.relationship('ObjectLink',
                            secondary='scrap_link',
                            back_populates='scraps')
