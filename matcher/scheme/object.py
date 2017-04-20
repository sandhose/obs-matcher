from sqlalchemy import Column, String, Sequence, Integer, ForeignKey, Table
from sqlalchemy.orm import relationship

from .utils import Base


scrap_link = Table(
    'scrap_link', Base.metadata,
    Column('scrap_id', ForeignKey('scrap.id'), primary_key=True),
    Column('object_link_id', ForeignKey('object_link.id'), primary_key=True),
)


class ExternalObject(Base):
    __tablename__ = 'external_object'

    id = Column(Integer, Sequence('external_object_id_seq'), primary_key=True)
    # @TODO
    # type = …


class ObjectLink(Base):
    __tablename__ = 'object_link'

    id = Column(Integer, Sequence('object_link_id_seq'), primary_key=True)
    object_id = Column(Integer, ForeignKey('external_object.id'),
                       nullable=False)
    platform_id = Column(Integer, ForeignKey('platform.id'), nullable=False)
    external_id = Column(String)

    object = relationship('ExternalObject', back_populates='links')
    platform = relationship('Platform', back_populates='links')
    scraps = relationship('Scrap', secondary='scrap_link',
                          back_populates='links')
    work_meta = relationship('ObjectLinkWorkMeta')


class ObjectLinkWorkMeta(Base):
    __tablename__ = 'object_link_work_meta'

    id = Column(Integer, ForeignKey('object_link.id'),
                nullable=False, primary_key=True)

    link = relationship('ObjectLink', back_populates='work_meta',
                        uselist=False)
