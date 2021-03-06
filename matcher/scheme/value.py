from sqlalchemy import (
    Column,
    Enum,
    ForeignKey,
    Integer,
    Sequence,
    Text,
    column,
    func,
    select,
    table,
)
from sqlalchemy.ext.hybrid import hybrid_property
from sqlalchemy.orm import column_property, relationship

from . import Base
from .enums import ValueType
from .platform import Platform

__all__ = ["Value", "ValueSource"]


class Value(Base):
    __tablename__ = "value"

    value_id_seq = Sequence("value_id_seq", metadata=Base.metadata)
    id = Column(
        Integer,
        value_id_seq,
        server_default=value_id_seq.next_value(),
        primary_key=True,
    )
    type = Column(Enum(ValueType, name="value_type"), nullable=False)
    external_object_id = Column(
        Integer,
        ForeignKey("external_object.id", ondelete="CASCADE", onupdate="CASCADE"),
        nullable=False,
    )
    text = Column(Text, nullable=False)

    external_object = relationship(
        "ExternalObject", cascade="all", back_populates="values"
    )
    sources = relationship("ValueSource", back_populates="value", cascade="all")

    @hybrid_property
    def score(self):
        return sum(source.score for source in self.sources)

    @score.expression
    def score(cls):
        return (
            select([func.sum(ValueSource.score)])
            .where(ValueSource.value_id == cls.id)
            .label("total_score")
        )

    cached_score = column_property(
        select([column("score")]).
        select_from(table("vw_value_score")).
        where(column("value_id") == id),
        deferred=True)

    def __str__(self):
        return "{}({}): {}".format(self.type, self.score, self.text)


class ValueSource(Base):
    __tablename__ = "value_source"

    value_id = Column(
        Integer,
        ForeignKey("value.id", ondelete="CASCADE", onupdate="CASCADE"),
        primary_key=True,
    )
    platform_id = Column(
        Integer,
        ForeignKey("platform.id", ondelete="CASCADE", onupdate="CASCADE"),
        primary_key=True,
    )
    score_factor = Column(Integer, nullable=False, default=100)
    comment = Column(Text)

    value = relationship("Value", back_populates="sources")
    platform = relationship("Platform")

    @hybrid_property
    def score(self):
        return self.platform.base_score * self.score_factor

    @score.expression
    def score(cls):
        return cls.score_factor * select([Platform.base_score]).where(
            Platform.id == cls.platform_id
        )
