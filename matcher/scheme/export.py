"""Exports related models."""

import codecs
import csv
import gzip
import re
from functools import partial
from typing import Any, Callable, Dict, Iterator, List, Set

from jinja2 import Environment, meta, nodes
from slugify import slugify
from sqlalchemy import (Column, Enum, ForeignKey, Integer, Sequence, String,
                        func, or_, select,)
from sqlalchemy.dialects.postgresql import HSTORE, JSONB
from sqlalchemy.orm import (contains_eager, object_session, relationship,
                            subqueryload,)

from .base import Base
from .enums import (ExportFactoryIterator, ExportFileStatus, ExportRowType,
                    ExternalObjectType, PlatformType,)

__all__ = ['ExportTemplate', 'ExportFactory', 'ExportFile']

csv_dialect = csv.excel_tab

ExportFactoryTemplateContext = Dict[str, Any]
ExportFileFilters = Dict[str, str]
ExportFileContext = Dict[str, Any]


class Attributes(object):
    def __init__(self, view):
        from .views import AttributesView
        self.view = view or AttributesView()

    def __getattr__(self, name):
        return getattr(self.view, name) or []


# TODO: move this
def _quote(field: Any) -> str:
    """Double-quotes a string if needed"""
    if isinstance(field, bool):
        return str(int(field))

    if field is None:
        return ""

    field = str(field)
    pattern = re.compile("(" + csv_dialect.quotechar + "|" + csv_dialect.delimiter + "|\n|\r)")
    if re.search(pattern, field) is not None:
        escaped = field.replace('\n', '\\n').replace('\r', '\\r')
        escaped = re.sub(pattern, r"\\\1", escaped)
        return '{quote}{field}{quote}'.format(quote=csv_dialect.quotechar,
                                              field=escaped)

    return field


_jinja_env = Environment()
_jinja_env.filters['quote'] = _quote
_jinja_env.filters['slugify'] = slugify
_jinja_env.filters['pathify'] = partial(slugify, separator='_')


class _zones(object):
    # FIXME: those are hard-coded, but they should be either loaded from config or from DB
    EUROBS = set(['AL', 'AM', 'AT', 'BA', 'BE', 'BG', 'CH', 'CY', 'CZ', 'DE', 'DK', 'EE', 'ES', 'FI', 'FR', 'GB', 'GE',
                  'GR', 'HR', 'HU', 'IE', 'IS', 'IT', 'LI', 'LT', 'LU', 'LV', 'ME', 'MK', 'MT', 'NL', 'NO', 'PL', 'PT',
                  'RO', 'RU', 'SE', 'SI', 'SK', 'TR'])
    EURCOE = set(['AD', 'AL', 'AM', 'AT', 'AZ', 'BA', 'BE', 'BG', 'BY', 'CH', 'CS', 'CY', 'CZ', 'DD', 'DE', 'DK', 'EE',
                  'ES', 'FI', 'FR', 'GB', 'GE', 'GI', 'GL', 'GR', 'HR', 'HU', 'IE', 'IS', 'IT', 'LI', 'LT', 'LU', 'LV',
                  'MC', 'MD', 'ME', 'MK', 'MT', 'NL', 'NO', 'PL', 'PT', 'RO', 'RS', 'RU', 'SE', 'SI', 'SK', 'SM', 'SU',
                  'TR', 'UA', 'VA', 'YU'])
    EUR28 = set(['AT', 'BE', 'BG', 'CY', 'CZ', 'DE', 'DK', 'EE', 'ES', 'FI', 'FR', 'GB', 'GR', 'HR', 'HU', 'IE', 'IT',
                 'LT', 'LU', 'LV', 'MT', 'NL', 'PL', 'PT', 'RO', 'SE', 'SI', 'SK'])
    EUREU = EUR28
    US = set(['US'])


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
    def needs(self) -> Set[str]:
        return meta.find_undeclared_variables(self.parsed_template)

    @property
    def parsed_template(self):
        return _jinja_env.parse(self.template)

    @property
    def links(self) -> List[str]:
        found_links = set()
        for n in self.parsed_template.find_all(nodes.Getitem):
            if isinstance(n.node, nodes.Name) \
                    and getattr(n.node, 'name') == "links" \
                    and getattr(n.node, "ctx") == "load":
                found_links.add(n.arg.value)  # It will raise if it is not a Const

        # Links are sorted because the order needs to be consistant when querying
        return sorted(found_links)

    def to_context(self, row) -> dict:
        """Maps a row from the `row_query` to a dict with everything needed for the template context"""

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
            context['attributes'] = Attributes(external_object.attributes)

        if 'zones' in needs:
            context['zones'] = _zones

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

        if 'platform' in needs and self.row_type == ExportRowType.EXTERNAL_OBJECT:
            raise Exception("Platform can't be queried when the row_type is EXTERNAL_OBJECT")

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
            query = (
                session.query(ExternalObject, *links_select).
                join(ObjectLink, ExternalObject.id == ObjectLink.external_object_id).
                group_by(ExternalObject.id)
            )
        elif self.row_type == ExportRowType.OBJECT_LINK:
            query = session.query(ObjectLink, ExternalObject, *links_select)\
                .join(ExternalObject, ExternalObject.id == ObjectLink.external_object_id)

        if 'attributes' in needs:
            query = query.options(subqueryload(ExternalObject.attributes))

        if 'platform' in needs:
            query = (
                query.
                join(Platform, ObjectLink.platform_id == Platform.id).
                options(contains_eager(ObjectLink.platform).joinedload(Platform.group))
            )

        query = query.filter(ExternalObject.type == self.external_object_type)

        return query

    def compile_template(self) -> Callable[[dict], str]:
        template = _jinja_env.from_string(self.template)
        return lambda context: template.render(**context)

    @property
    def template(self) -> str:
        return csv_dialect.delimiter.join(
            '{{{{ ({value}) | quote }}}}'.format(value=field.get('value', '""'))
            for field in self.fields
        )

    @property
    def header(self) -> str:
        return csv_dialect.delimiter.join((_quote(field.get('name', None)) for field in self.fields))


class ExportFactory(Base):
    __tablename__ = 'export_factory'

    export_factory_id_seq = Sequence('export_factory_id_seq', metadata=Base.metadata)
    id = Column(Integer, export_factory_id_seq, server_default=export_factory_id_seq.next_value(), primary_key=True)

    name = Column(String, nullable=False)

    export_template_id = Column(Integer, ForeignKey(ExportTemplate.id), nullable=False)
    template = relationship(ExportTemplate, back_populates='factories')

    iterator = Column(Enum(ExportFactoryIterator))  # can be NULL
    file_path_template = Column(String, nullable=False)
    filters_template = Column(HSTORE, nullable=False)

    files = relationship('ExportFile', back_populates='factory')

    def iterate(self, session=None) -> Iterator[ExportFactoryTemplateContext]:
        from . import Platform, PlatformGroup
        from .enums import PlatformType

        if session is None:
            session = object_session(self)

        query = session.query

        if self.iterator is ExportFactoryIterator.PLATFORMS:
            platforms = query(Platform).\
                filter(or_(Platform.type == PlatformType.TVOD, Platform.type == PlatformType.SVOD)).\
                filter(Platform.ignore_in_exports.is_(False))

            for platform in platforms:
                yield {'platform': platform}

        elif self.iterator is ExportFactoryIterator.GROUPS:
            for group in query(PlatformGroup):
                yield {'group': group}

        elif self.iterator is ExportFactoryIterator.COUNTRIES:
            countries = query(Platform.country).\
                order_by(Platform.country).\
                filter(func.char_length(Platform.country) == 2).\
                filter(or_(Platform.type == PlatformType.TVOD, Platform.type == PlatformType.SVOD)).\
                filter(Platform.ignore_in_exports.is_(False)).\
                distinct()

            # SQLA tends to return tuples even when there is only one column
            for (country, ) in countries:
                yield {'country': country}

        else:
            yield {}

    def compile_filters_template(self) -> Callable[[ExportFactoryTemplateContext], ExportFileFilters]:
        templates = [
            (key, _jinja_env.from_string(value))
            for (key, value) in self.filters_template.items()
        ]

        return lambda **context: {key: value.render(**context) for (key, value) in templates}

    def compile_path_template(self) -> Callable[[ExportFactoryTemplateContext], str]:
        template = _jinja_env.from_string(self.file_path_template)
        return lambda context: template.render(**context)

    def generate(self, scrap_session, session=None) -> Iterator['ExportFile']:
        path_template = self.compile_path_template()
        filters_template = self.compile_filters_template()

        for context in self.iterate(session=session):
            context = {
                'session': scrap_session,
                **context
            }

            yield ExportFile(factory=self,
                             template=self.template,
                             session=scrap_session,
                             path=path_template(context),
                             filters=filters_template(context))


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
        from .platform import Platform

        # TODO: apply filters
        query = self.template.row_query

        for (key, values) in self.filters.items():
            # A filter might look like `platform.id => 19, 51`
            context, attribute = key.split('.')
            # For now, we strip and uppercase each value
            values = [v.strip().upper() for v in values.split(',')]

            if context == 'platform':
                if not hasattr(Platform, attribute):
                    raise NotImplementedError

                # Cast accordingly
                if attribute == 'id' or attribute == 'group_id':
                    values = [int(v) for v in values]
                elif attribute == 'type':
                    values = [PlatformType.from_string(v) for v in values]

                query.filter(getattr(Platform, attribute).in_(values))
            else:
                raise NotImplementedError

        return query

    def row_contexts(self) -> Iterator[ExportFileContext]:
        return (self.template.to_context(row) for row in self.filtered_query)

    def render_rows(self) -> Iterator[str]:
        template = self.template.compile_template()
        for context in self.row_contexts():
            yield template(context)

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
