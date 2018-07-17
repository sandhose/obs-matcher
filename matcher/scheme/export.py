"""Exports related models."""

import codecs
import csv
import gzip
from typing import Iterator, List

from jinja2 import Environment
from sqlalchemy import (Column, Enum, ForeignKey, Integer, Sequence, String,
                        select,)
from sqlalchemy.dialects.postgresql import HSTORE, JSONB
from sqlalchemy.orm import joinedload, object_session, relationship

from .base import Base
from .enums import (ExportFileStatus, ExportFilterIterator, ExportRowType,
                    ExternalObjectType,)

__all__ = ['ExportTemplate', 'ExportFactory', 'ExportFile']

csv_dialect = csv.excel_tab


# TODO: move this
def _quote(field: any) -> str:
    """Double-quotes a string if needed"""
    if isinstance(field, bool):
        return int(field)

    if field is None:
        return ""

    field = str(field)
    if csv_dialect.delimiter in field or csv_dialect.quotechar in field:
        return '{quote}{field}{quote}'.format(quote=csv_dialect.quote,
                                              field=field.replace(csv_dialect.quotechar, '\\' + csv_dialect.quotechar))
    return field


_jinja_env = Environment()
_jinja_env.filters['quote'] = _quote


class _zones(object):
    def __getattr__(self, name):
        return set()


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
            current_link, *row = row
        else:
            current_link = None

        external_object, *links = row

        context = {}
        context['external_object'] = external_object
        context['links'] = dict(zip(self.links, links))

        if current_link is not None:
            context['links']['current'] = current_link.external_id

        if 'attributes' in needs:
            context['attributes'] = external_object.attributes \
                or AttributesView(titles=[], dates=[], genres=[], durations=[], names=[], countries=[])

        if 'zones' in needs:
            context['zones'] = _zones()  # TODO

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
            limit(1).
            correlate(ExternalObject).
            label(platform.slug)
            for platform in platforms
        ]

        if self.row_type == ExportRowType.EXTERNAL_OBJECT:
            query = session.query(ExternalObject, *links_select)
        elif self.row_type == ExportRowType.OBJECT_LINK:
            query = session.query(ObjectLink, ExternalObject, *links_select)\
                .join(ExternalObject, ExternalObject.id == ObjectLink.external_object_id)

        if 'attributes' in needs:
            query = query.options(joinedload(ExternalObject.attributes))

        if 'platform' in needs:
            if self.row_type == ExportRowType.EXTERNAL_OBJECT:
                raise Exception("Platform can't be queried when the row_type is EXTERNAL_OBJECT")
            query = query.options(joinedload(ObjectLink.platform).joinedload(Platform.group))

        query = query.filter(ExternalObject.type == self.external_object_type)

        return query

    def compile_template(self):
        return _jinja_env.from_string(self.template)

    @property
    def template(self) -> str:
        return csv_dialect.delimiter.join(
            '{{{{ ({value}) | quote }}}}'.format(value=field['value'])
            for field in self.fields
        )

    @property
    def header(self) -> str:
        return csv_dialect.delimiter.join((_quote(fields['name']) for fields in self.fields))

    @property
    def column_names(self) -> List[str]:
        return [field['name'] for field in self.fields]


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

    @property
    def filtered_query(self):
        # TODO: apply filters
        return self.template.row_query

    def row_contexts(self) -> Iterator[dict]:
        return (self.template.to_context(row) for row in self.filtered_query)

    def render_rows(self) -> Iterator[str]:
        template = self.template.compile_template()
        for contexts in self.row_contexts():
            yield template.render(**contexts)

    def render(self) -> Iterator[str]:
        yield self.template.header
        yield from self.render_rows()

    def process(self):
        # FIXME: move this to a task
        # FIXME: should we gzip on the fly? where do we store everything?
        with gzip.open(self.path + '.gz', 'wb') as file:
            # Write UTF16-LE BOM because Excel.
            file.write(codecs.BOM_UTF16_LE)
            for row in self.render():
                file.write((row + csv_dialect.lineterminator).encode('utf-16-le'))
