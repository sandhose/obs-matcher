import enum

from matcher import db


class Gender(enum.Enum):
    not_known = 0
    male = 1
    female = 2
    not_applicable = 9


class RoleType(enum.Enum):
    director = 0
    actor = 1
    writer = 2


class Role(db.Model):
    __tablename__ = 'role'
    __table_args__ = (
        db.PrimaryKeyConstraint('person_id', 'av_work_id'),
    )

    person_id = db.Column(db.Integer, db.ForeignKey('person.id'))
    av_work_id = db.Column(db.Integer, db.ForeignKey('av_work.id'))

    person = db.relationship('Person', foreign_keys=[person_id],
                             back_populates='roles')
    av_work = db.relationship('AVWork', foreign_keys=[av_work_id],
                              back_populates='roles')
    role = db.Column(db.Enum(RoleType, name='role'))


class Person(db.Model):
    __tablename__ = 'person'

    id = db.Column(db.Integer, db.Sequence('person_id_seq'), primary_key=True)

    external_object_id = db.Column(db.Integer,
                                   db.ForeignKey('external_object.id'),
                                   nullable=False)
    name_value_id = db.Column(db.Integer, db.ForeignKey('value_id.id'),
                              nullable=False)

    external_object = db.relationship('ExternalObject',
                                      foreign_keys=[external_object_id])
    name = db.relationship('ValueID', foreign_keys=[name_value_id])
    gender = db.Column(db.Enum(Gender, name='gender'))
    roles = db.relationship('Role', back_populates='person')
