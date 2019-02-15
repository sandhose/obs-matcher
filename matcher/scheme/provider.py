from sqlalchemy import (
    Column,
    ForeignKey,
    Integer,
    Sequence,
    Text,
    UniqueConstraint,
    column,
    func,
    select,
    table,
)
from sqlalchemy.orm import column_property, relationship

from . import Base


class Provider(Base):
    """An entity that provides data for one or many platforms"""

    __tablename__ = "provider"

    __table_args__ = (UniqueConstraint("slug"),)

    provider_id_seq = Sequence("provider_id_seq", metadata=Base.metadata)
    id = Column(
        Integer,
        provider_id_seq,
        server_default=provider_id_seq.next_value(),
        primary_key=True,
    )

    name = Column(Text, nullable=False)
    """A human readable name"""

    slug = Column(Text, nullable=False)
    """A unique identifier"""

    platforms = relationship(
        "Platform", back_populates="providers", secondary="provider_platform"
    )

    imports = relationship("ImportFile", back_populates="provider")

    platform_count = column_property(
        select([func.count("platform_id")])
        .select_from(table("provider_platform"))
        .where(column("provider_id") == id),
        deferred=True,
    )

    import_count = column_property(
        select([func.count("id")])
        .select_from(table("import_file"))
        .where(column("provider_id") == id),
        deferred=True,
    )

    @classmethod
    def search_filter(cls, term):
        return (
            func.to_tsvector("simple", cls.name).op("||")(
                func.to_tsvector("simple", cls.slug)
            )
        ).op("@@")(func.to_tsquery("simple", "'" + term + "':*"))


class ProviderPlatform(Base):
    __tablename__ = "provider_platform"

    platform_id = Column(
        Integer,
        ForeignKey("platform.id", ondelete="CASCADE", onupdate="CASCADE"),
        primary_key=True,
        nullable=False,
    )

    provider_id = Column(
        Integer,
        ForeignKey("provider.id", ondelete="CASCADE", onupdate="CASCADE"),
        primary_key=True,
        nullable=False,
    )

    platform = relationship("Platform")
    provider = relationship("Provider")
