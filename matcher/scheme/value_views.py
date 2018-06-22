from sqlalchemy import select, func, join

from . import Base
from .object import ExternalObject
from .value import ValueSource, Value
from .mixins import ViewMixin


class ValueScoreView(Base, ViewMixin):
    __tablename__ = 'vw_value_score'

    __materialized__ = True
    __selectable__ = (
        select([ValueSource.value_id.label('value_id'), func.sum(ValueSource.score).label('score')]).
        select_from(ValueSource).
        group_by(ValueSource.value_id)
    )


class ValueView(Base, ViewMixin):
    __tablename__ = 'vw_value'

    __materialized__ = True
    __selectable__ = (
        select([
            Value.id.label('value_id'),
            Value.type.label('value_type'),
            Value.text.label('value_text'),
            ValueScoreView.score.label('value_score'),
            Value.external_object_id.label('external_object_id'),
            ExternalObject.type.label('external_object_type'),
        ]).
        select_from(
            join(Value, ExternalObject, Value.external_object_id == ExternalObject.id).
            join(ValueScoreView, ValueScoreView.value_id == Value.id)
        )
    )
