from sqlalchemy import (
    CHAR,
    Column,
    Float,
    Index,
    Integer,
    Text,
    and_,
    cast,
    column,
    func,
    join,
    or_,
    outerjoin,
    select,
    table,
    text,
    tuple_,
)
from sqlalchemy.dialects.postgresql import ARRAY, aggregate_order_by, array, array_agg

from . import Base
from .enums import PlatformType, ValueType
from .mixins import ViewMixin
from .platform import Platform
from .utils import crosstab
from .value import Value, ValueSource


class ValueScoreView(Base, ViewMixin):
    __tablename__ = "vw_value_score"

    __table_args__ = {
        "selectable": select(
            [
                ValueSource.value_id.label("value_id"),
                func.sum(ValueSource.score).label("score"),
            ]
        )
        .select_from(ValueSource)
        .group_by(ValueSource.value_id),
        "dependencies": (ValueSource, Platform),
        "materialized": True,
        "indexes": (Index("pk_vw_value_score", "value_id", unique=True),),
    }


_attribute_filter = or_(
    Value.type == ValueType.TITLE,
    and_(Value.type == ValueType.DATE, Value.text.op("~")(r"^[1-2]\d\d\d$")),
    Value.type == ValueType.GENRES,
    and_(Value.type == ValueType.DURATION, Value.text.op("~")(r"^[0-9.]+$")),
    Value.type == ValueType.NAME,
    and_(Value.type == ValueType.COUNTRY, Value.text.op("~")(r"^[A-Z]{2}$")),
)


class PlatformSourceOrderByValueType(Base, ViewMixin):
    __tablename__ = "vw_000_platform_source_order_by_value_type"

    __materialized__ = True
    __table_args__ = {
        "selectable": select(
            [
                # we can't reference Value.external_object_id because of it's
                # relationship with ExternalObject, which depends on
                # AttributesView
                Column("external_object_id").label("val_eo_id"),
                Value.type.label("val_type"),
                Platform.id.label("pl_id"),
                Platform.name.label("pl_name"),
                Platform.type.label("pl_type"),
                func.max(Platform.base_score).label("pl_max_score"),
                func.row_number()
                .over(
                    partition_by=[Value.external_object_id, Value.type],
                    order_by=Platform.base_score.desc(),
                )
                .label("pl_order"),
            ]
        )
        .select_from(
            outerjoin(Value, ValueSource, Value.id == ValueSource.value_id).outerjoin(
                Platform, ValueSource.platform_id == Platform.id
            )
        )
        .where(and_(_attribute_filter, ValueSource.value_id.isnot(None)))
        .group_by(
            Value.external_object_id,
            Value.type,
            Platform.id,
            Platform.name,
            Platform.type,
        ),
        "materialized": True,
        "dependencies": (Platform, Value, ValueSource),
        "indexes": (
            Index(
                "ix_vw_platform_source_order_by_value_type_eo_type_pl",
                "val_eo_id",
                "val_type",
                "pl_id",
                unique=True,
            ),
            Index(
                "ix_vw_platform_source_order_by_value_type_order_type_eo",
                "pl_order",
                "val_type",
                "val_eo_id",
            ),
        ),
    }


_titles = Column("titles", ARRAY(Text))


class AttributesView(Base, ViewMixin):
    __tablename__ = "vw_attributes"

    __materialized__ = True
    __table_args__ = {
        "selectable": select(
            [
                Column("external_object_id", primary_key=True),
                _titles,
                Column("dates", ARRAY(Integer)),
                Column("genres", ARRAY(Text)),
                Column("durations", ARRAY(Float)),
                Column("names", ARRAY(Text)),
                Column("countries", ARRAY(CHAR(length=2))),
                # Build a search vector from the first four titles
                func.setweight(func.to_tsvector(func.coalesce(_titles[0], "")), "A")
                .op("||")(
                    func.setweight(func.to_tsvector(func.coalesce(_titles[1], "")), "B")
                )
                .op("||")(
                    func.setweight(func.to_tsvector(func.coalesce(_titles[2], "")), "C")
                )
                .op("||")(
                    func.setweight(func.to_tsvector(func.coalesce(_titles[3], "")), "D")
                )
                .label("search_vector"),
            ]
        ).select_from(
            crosstab(
                select(
                    [
                        Value.external_object_id,
                        Value.type,
                        func.coalesce(
                            array_agg(
                                aggregate_order_by(
                                    Value.text, ValueScoreView.score.desc()
                                )
                            ),
                            cast(text("'{}'"), ARRAY(Text)),
                        ),
                    ]
                )
                .select_from(
                    join(
                        Value, ValueScoreView, Value.id == ValueScoreView.value_id
                    ).join(ValueSource, Value.id == ValueSource.value_id)
                )
                .where(
                    and_(
                        _attribute_filter,
                        tuple_(
                            Value.external_object_id,
                            Value.type,
                            ValueSource.platform_id,
                        ).in_(
                            select(
                                [
                                    PlatformSourceOrderByValueType.val_eo_id,
                                    PlatformSourceOrderByValueType.val_type,
                                    PlatformSourceOrderByValueType.pl_id,
                                ]
                            )
                            .select_from(PlatformSourceOrderByValueType)
                            .where(
                                and_(
                                    PlatformSourceOrderByValueType.pl_order == 1,
                                    or_(
                                        PlatformSourceOrderByValueType.pl_type
                                        == PlatformType.INFO,
                                        PlatformSourceOrderByValueType.val_type
                                        == ValueType.TITLE,
                                    ),
                                )
                            )
                        ),
                    )
                )
                .group_by(Value.external_object_id, Value.type),
                table(
                    "ct",
                    column("external_object_id", Integer),
                    column("titles", ARRAY(Text)),
                    column("dates", ARRAY(Integer)),
                    column("genres", ARRAY(Text)),
                    column("durations", ARRAY(Float)),
                    column("names", ARRAY(Text)),
                    column("countries", ARRAY(CHAR(length=2))),
                ),
                categories=select([func.unnest(array([v.name for v in ValueType]))]),
                auto_order=False,
            )
        ),
        "dependencies": (
            Value,
            ValueScoreView,
            ValueSource,
            PlatformSourceOrderByValueType,
        ),
        "materialized": True,
        "indexes": (Index("pk_vw_attributes", "external_object_id", unique=True),),
    }
