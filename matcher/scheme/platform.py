from datetime import datetime
from matcher import db
from .mixins import ResourceMixin


class PlatformGroup(db.Model, ResourceMixin):
    __tablename__ = 'platform_group'

    id = db.Column(db.Integer,
                   db.Sequence('platform_group_id_seq'),
                   primary_key=True)
    name = db.Column(db.String,
                     nullable=False)

    platforms = db.relationship('Platform',
                                back_populates='group')

    def __init__(self, name):
        self.name = name

    def __repr__(self):
        return '<PlatformGroup "{}">'.format(self.name)


class Platform(db.Model, ResourceMixin):
    __tablename__ = 'platform'

    id = db.Column(db.Integer,
                   db.Sequence('platform_id_seq'),
                   primary_key=True)
    name = db.Column(db.String,
                     nullable=False)
    slug = db.Column(db.String,
                     nullable=False,
                     default='')
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
    links = db.relationship('ObjectLink',
                            back_populates='platform')

    def __init__(self, name, url=None, country=None, slug=None, max_rating=10,
                 base_score=100, group=None):
        self.name = name
        self.url = url
        self.country = country
        self.max_rating = max_rating
        self.base_score = base_score
        self.group = group

        if slug is None:
            slug = name.lower().replace(' ', '-')
        self.slug = slug

    def __repr__(self):
        return '<Platform {!r}>'.format(self.name)


class Scrap(db.Model, ResourceMixin):
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

    def __init__(self, platform):
        self.platform = platform
        self.date = datetime.now()

    def __repr__(self):
        return '<Scrap ({}, {})>'.format(self.platform, self.date)
