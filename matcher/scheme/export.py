"""Exports related models."""

from typing import Iterator, List

from sqlalchemy import (Column, Enum, ForeignKey, Integer, Sequence, String,
                        select,)
from sqlalchemy.dialects.postgresql import HSTORE, JSONB
from sqlalchemy.orm import joinedload, object_session, relationship

from .base import Base
from .enums import (ExportFileStatus, ExportFilterIterator, ExportRowType,
                    ExternalObjectType,)

__all__ = ['ExportTemplate', 'ExportFactory', 'ExportFile']


class ExportTemplate(Base):
    __tablename__ = 'export_template'

    export_template_id_seq = Sequence('export_template_id_seq', metadata=Base.metadata)
    id = Column(Integer, export_template_id_seq, server_default=export_template_id_seq.next_value(), primary_key=True)

    row_type = Column(Enum(ExportRowType), nullable=False)
    external_object_type = Column(Enum(ExternalObjectType), nullable=False)
    fields = Column(JSONB, nullable=False)  # FIXME: how do we store fields?

    factories = relationship('ExportFactory', back_populates='template')
    files = relationship('ExportFile', back_populates='template')

    @property
    def needs(self) -> List[str]:
        return set((need for field in self.fields for need in field['needs']))

    @property
    def links(self) -> List[str]:
        return [need.split('.')[1] for need in self.needs if 'links' in need]

    def to_context(self, row) -> dict:
        """Maps a row from the `row_query` to a dict with everything needed for the template context"""
        from .views import AttributesView

        needs = self.needs

        # When iterating over the ObjectLinks, the first element of the row is the link itself
        # The rest of the columns are the same
        if self.row_type == ExportRowType.OBJECT_LINK:
            current_link, row = row
        else:
            current_link = None

        external_object, *links = row

        context = {}
        context['external_object'] = external_object
        context['links'] = dict(zip(self.links, links))

        if current_link is not None:
            context['links']['current'] = current_link.external_id

        if 'attributes' in needs:
            context['attributes'] = external_object.attributes or AttributesView()

        if 'zones' in needs:
            context['zones'] = []  # TODO

        if 'platform' in needs:
            if current_link is None:
                raise Exception("Platform can't be queried when the row_type is EXTERNAL_OBJECT")

            context['platform'] = current_link.platform

        return context

    @property
    def row_query(self):
        from .object import ObjectLink, ExternalObject
        from .platform import Platform

        session = object_session(self)
        needs = self.needs

        platforms = [Platform.lookup(session, slug) for slug in self.links]
        links_select = [
            select([ObjectLink.external_id]).
            where(ObjectLink.platform == platform).
            where(ObjectLink.external_object_id == ExternalObject.id).
            correlate(ExternalObject).
            label(platform.slug)
            for platform in platforms
        ]

        if self.row_type == ExportRowType.EXTERNAL_OBJECT:
            query = session.query(ExternalObject, *links_select)
        elif self.row_type == ExportRowType.OBJECT_LINK:
            query = session.query(ObjectLink, ExternalObject, *links_select)

        if 'attributes' in needs:
            query = query.options(joinedload(ExternalObject.attributes))

        if 'platform' in needs:
            if self.row_type == ExportRowType.EXTERNAL_OBJECT:
                raise Exception("Platform can't be queried when the row_type is EXTERNAL_OBJECT")
            query = query.options(joinedload(ObjectLink.platform).joinedload(Platform.group))

        query = query.filter(ExternalObject.type == self.external_object_type)

        return query

    def row_contexts(self) -> Iterator[dict]:
        return (self.to_context(row) for row in self.row_query)


class ExportFactory(Base):
    __tablename__ = 'export_factory'

    export_factory_id_seq = Sequence('export_factory_id_seq', metadata=Base.metadata)
    id = Column(Integer, export_factory_id_seq, server_default=export_factory_id_seq.next_value(), primary_key=True)

    name = Column(String, nullable=False)

    export_template_id = Column(Integer, ForeignKey(ExportTemplate.id), nullable=False)
    template = relationship(ExportTemplate, back_populates='factories')

    iterator = Column(Enum(ExportFilterIterator))  # can be NULL
    file_path_template = Column(String, nullable=False)
    filters_template = Column(HSTORE, nullable=False)

    files = relationship('ExportFile', back_populates='factory')


class ExportFile(Base):
    __tablename__ = 'export_file'

    export_file_id_seq = Sequence('export_file_id_seq', metadata=Base.metadata)
    id = Column(Integer, export_file_id_seq, server_default=export_file_id_seq.next_value(), primary_key=True)

    status = Column(Enum(ExportFileStatus),
                    default=ExportFileStatus.PROCESSING, server_default='PROCESSING', nullable=False)
    path = Column(String, nullable=False)
    filters = Column(HSTORE, nullable=False)

    export_template_id = Column(Integer, ForeignKey(ExportTemplate.id))
    template = relationship('ExportTemplate', back_populates='files')

    export_factory_id = Column(Integer, ForeignKey(ExportFactory.id))
    factory = relationship('ExportFactory', back_populates='files')

    session_id = Column(Integer, ForeignKey('session.id'), nullable=False)

    session = relationship('Session', back_populates='files')
