"""Exports related models."""

import codecs
import csv
import gzip
import re
from collections import OrderedDict
from functools import partial
from typing import Any, Callable, Dict, Iterator, List, Set

from celery import Celery
from jinja2 import Environment, StrictUndefined, meta, nodes
from slugify import slugify
from sqlalchemy import (
    TIMESTAMP,
    Column,
    Enum,
    ForeignKey,
    Integer,
    Sequence,
    String,
    any_,
    column,
    func,
    or_,
    select,
    table,
)
from sqlalchemy.dialects.postgresql import HSTORE, JSONB
from sqlalchemy.orm import column_property, contains_eager, relationship, subqueryload

from matcher.utils import export_path

from .base import Base
from .enums import (
    ExportFactoryIterator,
    ExportFileStatus,
    ExportRowType,
    ExternalObjectType,
    PlatformType,
)
from .utils import after, after_save, before, inject_session

__all__ = ["ExportTemplate", "ExportFactory", "ExportFile"]

csv_dialect = csv.excel_tab

ExportFactoryTemplateContext = Dict[str, Any]
ExportFileFilters = Dict[str, str]
ExportFileContext = Dict[str, Any]


class AttributesWrapper(object):
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
    pattern = re.compile(
        "(" + csv_dialect.quotechar + "|" + csv_dialect.delimiter + "|\n|\r)"
    )
    if re.search(pattern, field) is not None:
        escaped = field.replace("\n", "\\n").replace("\r", "\\r").replace('"', '""')
        return "{quote}{field}{quote}".format(
            quote=csv_dialect.quotechar, field=escaped
        )

    return field


_jinja_env = Environment()
_jinja_env.filters["quote"] = _quote
_jinja_env.filters["slugify"] = slugify
_jinja_env.filters["pathify"] = partial(slugify, separator="_")

_factory_jinja_env = _jinja_env.overlay(undefined=StrictUndefined)


class _zones(object):
    # FIXME: those are hard-coded, but they should be either loaded from config or from DB
    EUROBS = set(
        [
            "AL",
            "AM",
            "AT",
            "BA",
            "BE",
            "BG",
            "CH",
            "CY",
            "CZ",
            "DE",
            "DK",
            "EE",
            "ES",
            "FI",
            "FR",
            "GB",
            "GE",
            "GR",
            "HR",
            "HU",
            "IE",
            "IS",
            "IT",
            "LI",
            "LT",
            "LU",
            "LV",
            "ME",
            "MK",
            "MT",
            "NL",
            "NO",
            "PL",
            "PT",
            "RO",
            "RU",
            "SE",
            "SI",
            "SK",
            "TR",
        ]
    )
    EURCOE = set(
        [
            "AD",
            "AL",
            "AM",
            "AT",
            "AZ",
            "BA",
            "BE",
            "BG",
            "BY",
            "CH",
            "CS",
            "CY",
            "CZ",
            "DD",
            "DE",
            "DK",
            "EE",
            "ES",
            "FI",
            "FR",
            "GB",
            "GE",
            "GI",
            "GL",
            "GR",
            "HR",
            "HU",
            "IE",
            "IS",
            "IT",
            "LI",
            "LT",
            "LU",
            "LV",
            "MC",
            "MD",
            "ME",
            "MK",
            "MT",
            "NL",
            "NO",
            "PL",
            "PT",
            "RO",
            "RS",
            "RU",
            "SE",
            "SI",
            "SK",
            "SM",
            "SU",
            "TR",
            "UA",
            "VA",
            "YU",
        ]
    )
    EUR28 = set(
        [
            "AT",
            "BE",
            "BG",
            "CY",
            "CZ",
            "DE",
            "DK",
            "EE",
            "ES",
            "FI",
            "FR",
            "GB",
            "GR",
            "HR",
            "HU",
            "IE",
            "IT",
            "LT",
            "LU",
            "LV",
            "MT",
            "NL",
            "PL",
            "PT",
            "RO",
            "SE",
            "SI",
            "SK",
        ]
    )
    EUREU = EUR28
    US = set(["US"])


class ExportTemplate(Base):
    __tablename__ = "export_template"

    export_template_id_seq = Sequence("export_template_id_seq", metadata=Base.metadata)
    id = Column(
        Integer,
        export_template_id_seq,
        server_default=export_template_id_seq.next_value(),
        primary_key=True,
    )

    row_type = Column(Enum(ExportRowType), nullable=False)
    external_object_type = Column(Enum(ExternalObjectType), nullable=False)
    fields = Column(JSONB, nullable=False)  # FIXME: how do we store fields?

    factories = relationship("ExportFactory", back_populates="template")
    files = relationship("ExportFile", back_populates="template")

    @property
    def needs(self) -> Set[str]:
        """Find the needed context keys from the template"""
        return meta.find_undeclared_variables(self._parsed_template)

    @property
    def _parsed_template(self):
        return _jinja_env.parse(self.template)

    def __str__(self):
        return "Template #{id} on `{external_object_type}` using `{row_type}`".format(
            **vars(self)
        )

    @property
    def links(self) -> List[str]:
        """Find links from the fields value template"""
        found_links = set()
        for n in self._parsed_template.find_all(nodes.Getitem):
            # Check if it is the `links` variable that is being accessed
            if (
                isinstance(n.node, nodes.Name)
                and getattr(n.node, "name") == "links"
                and getattr(n.node, "ctx") == "load"
            ):
                found_links.add(n.arg.value)  # It might raise if it is not a Const

        # Links are sorted because the order needs to be consistent when querying
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

        external_object, *row = row

        context = {"external_object": external_object}

        # Extract the attributes in the correct order (see WARN in `get_row_query`)
        for attr in [
            "platform_countries",
            "platform_names",
            "seasons_count",
            "episodes_count",
        ]:
            if attr in needs:
                value, *row = row
                context[attr] = value

        links = row

        context["links"] = dict(zip(self.links, links))

        if current_link is not None:
            context["links"]["current"] = current_link.external_id

        if "platform_countries" in context:
            if None in context["platform_countries"]:
                context["platform_countries"].remove(None)

        if "attributes" in needs:
            context["attributes"] = AttributesWrapper(external_object.attributes)

        if "zones" in needs:
            context["zones"] = _zones

        if "platform" in needs:
            if current_link is None:
                raise Exception(
                    "Platform can't be queried when the row_type is EXTERNAL_OBJECT"
                )

            context["platform"] = current_link.platform

        return context

    @property
    def valid_template(self):
        allowed_fields = ["external_object", "zones", "links", "attributes"]

        if self.row_type == ExportRowType.OBJECT_LINK:
            allowed_fields.append("platform")
        elif self.row_type == ExportRowType.EXTERNAL_OBJECT:
            allowed_fields.extend(["platform_names", "platform_countries"])

        if self.external_object_type == ExternalObjectType.SERIES:
            allowed_fields.extend(["episodes_count", "seasons_count"])

        return all(need in allowed_fields for need in self.needs)

    @inject_session
    def get_row_query(self, session=None):
        from .object import ObjectLink, ExternalObject, Episode
        from .platform import Platform

        needs = self.needs

        if "platform" in needs and self.row_type == ExportRowType.EXTERNAL_OBJECT:
            raise Exception(
                "Platform can't be queried when the row_type is EXTERNAL_OBJECT"
            )

        platforms = [Platform.lookup(session, slug) for slug in self.links]
        links_select = [
            select([ObjectLink.external_id])
            .where(ObjectLink.platform == platform)
            .where(ObjectLink.external_object_id == ExternalObject.id)
            .limit(1)
            .correlate(ExternalObject)
            .label(platform.slug)
            for platform in platforms
        ]

        def filter_platform(q, platform_id):
            # misc function to filter on a platform, depending on the row_type
            if self.row_type == ExportRowType.EXTERNAL_OBJECT:
                return q.filter(platform_id == any_(func.array_agg(Platform.id)))
            elif self.row_type == ExportRowType.OBJECT_LINK:
                return q.filter(platform_id == Platform.id)

        # WARN: this needs to be an ordered dict, because python3.5 does not
        # keep the order on defaultdict while python3.6 does.
        extra_attributes = OrderedDict(
            [
                ("platform_countries", func.array_agg(func.distinct(Platform.country))),
                ("platform_names", func.array_agg(Platform.name)),
                (
                    "seasons_count",
                    filter_platform(
                        session.query(func.count(func.distinct(Episode.season)))
                        .join(
                            ObjectLink,
                            Episode.external_object_id == ObjectLink.external_object_id,
                        )
                        .filter(Episode.series_id == ExternalObject.id),
                        ObjectLink.platform_id,
                    ),
                ),
                (
                    "episodes_count",
                    filter_platform(
                        session.query(
                            func.count(func.distinct(Episode.season, Episode.episode))
                        )
                        .join(
                            ObjectLink,
                            Episode.external_object_id == ObjectLink.external_object_id,
                        )
                        .filter(Episode.series_id == ExternalObject.id),
                        ObjectLink.platform_id,
                    ),
                ),
            ]
        )

        extra_select = [
            value.label(key) for key, value in extra_attributes.items() if key in needs
        ]

        if self.row_type == ExportRowType.EXTERNAL_OBJECT:
            query = (
                session.query(ExternalObject, *extra_select, *links_select)
                .join(ObjectLink, ExternalObject.id == ObjectLink.external_object_id)
                .join(Platform, ObjectLink.platform_id == Platform.id)
                .group_by(ExternalObject.id)
            )
        elif self.row_type == ExportRowType.OBJECT_LINK:
            query = (
                session.query(ObjectLink, ExternalObject, *extra_select, *links_select)
                .join(Platform, ObjectLink.platform_id == Platform.id)
                .join(
                    ExternalObject, ObjectLink.external_object_id == ExternalObject.id
                )
                .options(contains_eager(ObjectLink.platform).joinedload(Platform.group))
            )

        if "attributes" in needs:
            query = query.options(subqueryload(ExternalObject.attributes))

        query = query.filter(ExternalObject.type == self.external_object_type)

        return query

    def compile_template(self) -> Callable[[dict], str]:
        template = _jinja_env.from_string(self.template)
        return lambda context: template.render(**context)

    @property
    def template(self) -> str:
        return csv_dialect.delimiter.join(
            "{{{{ ({value}) | quote }}}}".format(value=field.get("value", '""'))
            for field in self.fields
        )

    @property
    def header(self) -> str:
        return csv_dialect.delimiter.join(
            (_quote(field.get("name", None)) for field in self.fields)
        )


class ExportFactory(Base):
    __tablename__ = "export_factory"

    export_factory_id_seq = Sequence("export_factory_id_seq", metadata=Base.metadata)
    id = Column(
        Integer,
        export_factory_id_seq,
        server_default=export_factory_id_seq.next_value(),
        primary_key=True,
    )

    name = Column(String, nullable=False)

    export_template_id = Column(Integer, ForeignKey(ExportTemplate.id), nullable=False)
    template = relationship(ExportTemplate, back_populates="factories")

    iterator = Column(Enum(ExportFactoryIterator))  # can be NULL
    file_path_template = Column(String, nullable=False)
    filters_template = Column(HSTORE, nullable=False)

    files = relationship("ExportFile", back_populates="factory")

    @inject_session
    def iterate(self, session=None) -> Iterator[ExportFactoryTemplateContext]:
        from . import Platform, PlatformGroup
        from .enums import PlatformType

        query = session.query

        if self.iterator is ExportFactoryIterator.PLATFORMS:
            platforms = (
                query(Platform)
                .filter(
                    or_(
                        Platform.type == PlatformType.TVOD,
                        Platform.type == PlatformType.SVOD,
                    )
                )
                .filter(Platform.ignore_in_exports.is_(False))
            )

            for platform in platforms:
                yield {"platform": platform}

        elif self.iterator is ExportFactoryIterator.GROUPS:
            for group in query(PlatformGroup):
                yield {"group": group}

        elif self.iterator is ExportFactoryIterator.COUNTRIES:
            countries = (
                query(Platform.country)
                .order_by(Platform.country)
                .filter(func.char_length(Platform.country) == 2)
                .filter(
                    or_(
                        Platform.type == PlatformType.TVOD,
                        Platform.type == PlatformType.SVOD,
                    )
                )
                .filter(Platform.ignore_in_exports.is_(False))
                .distinct()
            )

            # SQLA tends to return tuples even when there is only one column
            for (country,) in countries:
                yield {"country": country}

        else:
            yield {}

    def compile_filters_template(
        self
    ) -> Callable[[ExportFactoryTemplateContext], ExportFileFilters]:
        templates = [
            (key, _factory_jinja_env.from_string(value))
            for (key, value) in self.filters_template.items()
        ]

        return lambda context: {
            key: value.render(**context) for (key, value) in templates
        }

    def compile_path_template(self) -> Callable[[ExportFactoryTemplateContext], str]:
        template = _factory_jinja_env.from_string(self.file_path_template)
        return lambda context: template.render(**context)

    @inject_session
    def generate(self, scrap_session, session=None) -> Iterator["ExportFile"]:
        path_template = self.compile_path_template()
        filters_template = self.compile_filters_template()

        for context in self.iterate(session=session):
            context = {"session": scrap_session, **context}

            yield ExportFile(
                factory=self,
                template=self.template,
                session=scrap_session,
                path=path_template(context),
                filters=filters_template(context),
            )


@ExportFileStatus.act_as_statemachine("status")
class ExportFile(Base):
    __tablename__ = "export_file"

    export_file_id_seq = Sequence("export_file_id_seq", metadata=Base.metadata)
    id = Column(
        Integer,
        export_file_id_seq,
        server_default=export_file_id_seq.next_value(),
        primary_key=True,
    )

    status = Column(Enum(ExportFileStatus), default=None, nullable=False)
    path = Column(String, nullable=False)
    filters = Column(HSTORE, nullable=False)

    export_template_id = Column(Integer, ForeignKey(ExportTemplate.id))
    template = relationship("ExportTemplate", back_populates="files")

    export_factory_id = Column(Integer, ForeignKey(ExportFactory.id))
    factory = relationship("ExportFactory", back_populates="files")

    session_id = Column(Integer, ForeignKey("session.id"), nullable=False)

    session = relationship("Session", back_populates="files")
    logs = relationship("ExportFileLog", back_populates="file")

    last_activity = column_property(
        select([column("timestamp")])
        .select_from(table("export_file_log"))
        .where(column("export_file_id") == id)
        .order_by(column("timestamp").desc())
        .limit(1),
        deferred=True,
    )

    @inject_session
    def get_filtered_query(self, session=None):
        assert self.template.valid_template, "invalid template"

        query = self.template.get_row_query(session=session)
        return self.filter_query(query)

    def filter_query(self, query):
        from .object import ObjectLink

        # FIXME: THIS DOES NOT TAKE THE scrap_session INTO ACCOUNT
        from .platform import Platform, Scrap, Session
        from .import_ import ImportFile

        session = query.session  # i guess this works

        # FIXME: way to override this?
        query = query.filter(Platform.ignore_in_exports.is_(False))

        import_file_query = (
            session.query(ObjectLink.id)
            .join(ObjectLink.imports)
            .join(ImportFile.sessions)
            .filter(Session.id == self.session.id)
        )

        session_query = (
            session.query(ObjectLink.id)
            .join(ObjectLink.scraps)
            .join(Scrap.sessions)
            .filter(Session.id == self.session.id)
        )

        query = query.filter(ObjectLink.id.in_(session_query.union(import_file_query)))

        for (key, values) in self.filters.items():
            # A filter might look like `platform.id => 19, 51`
            context, attribute = key.split(".")
            # For now, we strip and uppercase each value
            values = [v.strip().upper() for v in values.split(",")]

            if context == "platform":
                if not hasattr(Platform, attribute):
                    raise NotImplementedError

                # Cast accordingly
                if attribute == "id" or attribute == "group_id":
                    values = [None if v in ["NONE", "NULL"] else int(v) for v in values]
                elif attribute == "type":
                    values = [PlatformType.from_name(v) for v in values]

                if None in values:
                    # `WHERE X IN (NULL)` does not work with postgres, so we have to handle this special case
                    query = query.filter(
                        or_(
                            getattr(Platform, attribute).in_(
                                v for v in values if v is not None
                            ),
                            getattr(Platform, attribute).is_(None),
                        )
                    )
                else:
                    query = query.filter(getattr(Platform, attribute).in_(values))

            else:
                raise NotImplementedError

        return query

    @inject_session
    def count_links(self, session=None):
        from .object import ObjectLink, ExternalObject

        query = (
            session.query(ExternalObject)
            .join(ExternalObject.links)
            .join(ObjectLink.platform)
            .filter(ExternalObject.type == self.template.external_object_type)
        )
        return self.filter_query(query).count()

    @inject_session
    def row_contexts(self, session=None) -> Iterator[ExportFileContext]:
        return (
            self.template.to_context(row)
            for row in self.get_filtered_query(session=session)
        )

    @inject_session
    def render_rows(self, session=None) -> Iterator[str]:
        template = self.template.compile_template()
        for context in self.row_contexts(session=session):
            yield template(context)

    @inject_session
    def render(self, session=None) -> Iterator[str]:
        yield self.template.header
        yield from self.render_rows(session=session)

    @property
    def real_name(self):
        return "{id}.csv.gz".format(id=self.id)

    def open(self, *args, **kwargs):
        return (export_path() / self.real_name).open(*args, **kwargs)

    @before("delete")
    def delete_file(self, *_, **__):
        export_path(self.real_name).unlink()

    @after_save("schedule")
    def schedule_task(self, celery, *_, **__):
        assert isinstance(celery, Celery)
        celery.send_task("matcher.tasks.export.process_file", [self.id], countdown=3)

    @after
    def log_status(self, message=None, *_, **__):
        self.logs.append(ExportFileLog(status=self.status, message=message))

    @after("start")
    @inject_session
    def process(self, session=None):
        # FIXME: this supposes that the object is already in the session
        # FIXME: move this to a task
        # FIXME: should we gzip on the fly? where do we store everything?
        with gzip.open(self.open(mode="wb"), "wb") as file:
            # Write UTF16-LE BOM because Excel.
            file.write(codecs.BOM_UTF16_LE)

            for index, row in enumerate(self.render(session=session)):
                file.write((row + csv_dialect.lineterminator).encode("utf-16-le"))

                # FIXME: quite ugly but it works
                if index == 1:  # We passed the header row
                    self.processing()
                    session.add(self)
                    session.commit()


class ExportFileLog(Base):
    __tablename__ = "export_file_log"

    export_file_log_id_seq = Sequence("export_file_log_id_seq", metadata=Base.metadata)
    id = Column(
        Integer,
        export_file_log_id_seq,
        server_default=export_file_log_id_seq.next_value(),
        primary_key=True,
    )

    export_file_id = Column(
        Integer,
        ForeignKey(ExportFile.id, ondelete="CASCADE", onupdate="CASCADE"),
        nullable=False,
    )
    file = relationship("ExportFile", back_populates="logs")

    timestamp = Column(
        TIMESTAMP(timezone=True), server_default=func.now(), nullable=False
    )
    status = Column(Enum(ExportFileStatus), nullable=False)
    message = Column(String)
