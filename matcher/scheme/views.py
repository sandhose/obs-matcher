from sqlalchemy import (CHAR, Column, Float, Integer, Text, and_, column, func,
                        join, or_, select, table,)
from sqlalchemy.dialects.postgresql import (ARRAY, aggregate_order_by, array,
                                            array_agg,)

from . import Base
from .enums import ValueType
from .mixins import ViewMixin
from .utils import crosstab
from .value import Value, ValueSource


class ValueScoreView(Base, ViewMixin):
    __tablename__ = 'vw_value_score'

    __materialized__ = True
    __selectable__ = (
        select([ValueSource.value_id.label('value_id'), func.sum(ValueSource.score).label('score')]).
        select_from(ValueSource).
        group_by(ValueSource.value_id)
    )


class AttributesView(Base, ViewMixin):
    __tablename__ = 'vw_attributes'

    __materialized__ = True
    __selectable__ = (
        select([
            Column('external_object_id', primary_key=True),
            Column('titles'),
            Column('dates'),
            Column('genres'),
            Column('durations'),
            Column('names'),
            Column('countries')
        ]).
        select_from(crosstab(
            select([Value.external_object_id,
                    Value.type,
                    array_agg(aggregate_order_by(Value.text, ValueScoreView.score.desc()))]).
            select_from(join(Value, ValueScoreView, Value.id == ValueScoreView.value_id)).
            where(or_(
                Value.type == ValueType.TITLE,
                and_(Value.type == ValueType.DATE, Value.text.op('~')(r'^[1-2]\d\d\d$')),
                Value.type == ValueType.GENRES,
                and_(Value.type == ValueType.DURATION, Value.text.op('~')(r'^[0-9.]+$')),
                Value.type == ValueType.NAME,
                and_(Value.type == ValueType.COUNTRY, Value.text.op('~')(r'^[A-Z][A-Z]$'))
            )).
            group_by(Value.external_object_id, Value.type),
            table('ct',
                  column('external_object_id', Integer),
                  column('titles', ARRAY(Text)),
                  column('dates', ARRAY(Integer)),
                  column('genres', ARRAY(Text)),
                  column('durations', ARRAY(Float)),
                  column('names', ARRAY(Text)),
                  column('countries', ARRAY(CHAR(length=2)))),
            categories=select([func.unnest(array([v.name for v in ValueType]))]),
            auto_order=False
        ))
    )
