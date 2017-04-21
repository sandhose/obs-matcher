from matcher import db


class ValueID(db.Model):
    __tablename__ = 'value_id'

    id = db.Column(db.Integer, db.Sequence('value_id_id_seq'),
                   primary_key=True)

    values = db.relationship('Value',
                             back_populates='value_id')


class Value(db.Model):
    __tablename__ = 'value'

    id = db.Column(db.Integer,
                   db.Sequence('value_id_seq'),
                   primary_key=True)
    value_id_id = db.Column(db.Integer,
                            db.ForeignKey('value_id.id'),
                            nullable=False)
    text = db.Column(db.String, nullable=False)

    value_id = db.relationship('ValueID',
                               back_populates='values')
    sources = db.relationship('Platform',
                              secondary='value_source',
                              back_populates='values')


class ValueSource(db.Model):
    __tablename__ = 'value_source'

    id_value = db.Column(db.Integer,
                         db.ForeignKey('value.id'),
                         primary_key=True)
    id_platform = db.Column(db.Integer,
                            db.ForeignKey('platform.id'),
                            primary_key=True)
    score_factor = db.Column(db.Integer,
                             nullable=False,
                             default=100)
