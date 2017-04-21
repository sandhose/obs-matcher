from matcher import db


scrap_link = db.Table(
    'scrap_link',
    db.Column('scrap_id', db.ForeignKey('scrap.id'), primary_key=True),
    db.Column('object_link_id', db.ForeignKey('object_link.id'),
              primary_key=True),
)


class ExternalObject(db.Model):
    __tablename__ = 'external_object'

    id = db.Column(db.Integer, db.Sequence('external_object_id_seq'),
                   primary_key=True)
    # @TODO
    # type = …


class ObjectLink(db.Model):
    __tablename__ = 'object_link'

    id = db.Column(db.Integer, db.Sequence('object_link_id_seq'),
                   primary_key=True)
    object_id = db.Column(db.Integer, db.ForeignKey('external_object.id'),
                          nullable=False)
    platform_id = db.Column(db.Integer, db.ForeignKey('platform.id'),
                            nullable=False)
    external_id = db.Column(db.String)

    object = db.relationship('ExternalObject', back_populates='links')
    platform = db.relationship('Platform', back_populates='links')
    scraps = db.relationship('Scrap', secondary='scrap_link',
                             back_populates='links')
    work_meta = db.relationship('ObjectLinkWorkMeta')


class ObjectLinkWorkMeta(db.Model):
    __tablename__ = 'object_link_work_meta'

    id = db.Column(db.Integer, db.ForeignKey('object_link.id'),
                   nullable=False, primary_key=True)

    link = db.relationship('ObjectLink', back_populates='work_meta',
                           uselist=False)
