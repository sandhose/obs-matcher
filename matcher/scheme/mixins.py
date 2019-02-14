from sqlalchemy import Column, event
from sqlalchemy.ext import compiler
from sqlalchemy.schema import DDLElement, SchemaItem
from sqlalchemy.sql import ColumnCollection
from sqlalchemy.sql.compiler import SQLCompiler
from sqlalchemy.sql.ddl import CreateIndex, DDLBase
from sqlalchemy.sql.elements import quoted_name
from sqlalchemy.sql.selectable import TableClause
from sqlalchemy.sql.visitors import Visitable


class CreateView(DDLElement):
    __visit_name__ = "create_view"

    def __init__(self, element):
        self.element = element


class DropView(DDLElement):
    __visit_name__ = "drop_view"

    def __init__(self, element):
        self.element = element


class RefreshMaterializedView(DDLElement):
    __visit_name__ = "refresh_materialized_view"

    def __init__(self, element):
        self.element = element


@compiler.compiles(CreateView)
def compile_create_view(element, compiler, **kw):
    f = (
        "CREATE MATERIALIZED VIEW IF NOT EXISTS {name} AS {selectable}"
        if element.element.materialized
        else "CREATE VIEW OR REPLACE {name} AS {selectable}"
    )

    return f.format(
        name=element.element.fullname,
        selectable=compiler.sql_compiler.process(
            element.element._view_select, literal_binds=True
        ),
    )


@compiler.compiles(DropView)
def compile_drop_view(element, compiler, **kw):
    return "DROP {type} IF EXISTS {name}".format(
        type=("MATERIALIZED VIEW" if element.element.materialized else "VIEW"),
        name=element.element.fullname,
    )


@compiler.compiles(RefreshMaterializedView)
def compile_refresh_materialized_view(element, compiler, **kw):
    return "REFRESH MATERIALIZED VIEW {name}".format(name=element.element.fullname)


class CreateViewVisitor(DDLBase):
    def visit_view(self, view, **kw):
        self.connection.execute(CreateView(view))

        if hasattr(view, "indexes"):
            for index in view.indexes:
                self.traverse_single(index)

    def visit_index(self, index):
        self.connection.execute(CreateIndex(index))


class DropViewVisitor(DDLBase):
    def visit_view(self, view, **kw):
        self.connection.execute(DropView(view))


def _visit_view(
    self,
    view,
    asfrom=False,
    iscrud=False,
    ashint=False,
    fromhints=None,
    use_schema=True,
    **kwargs,
):
    if asfrom or ashint:
        effective_schema = self.preparer.schema_for_object(view)

        if use_schema and effective_schema:
            ret = (
                self.preparer.quote_schema(effective_schema)
                + "."
                + self.preparer.quote(view.name)
            )
        else:
            ret = self.preparer.quote(view.name)
        if fromhints and view in fromhints:
            ret = self.format_from_hint_text(ret, view, fromhints[view], iscrud)
        return ret
    else:
        return ""


SQLCompiler.visit_view = _visit_view  # Monkey-patch SQLCompiler


_hooked_metadatas = set()


def _register_views_hooks(metadata):
    # This hooks on the metadata creation to add a new visitor that creates the
    # views
    @event.listens_for(metadata, "before_create")
    def before_create(target, connection, _ddl_runner=None, **kw):
        _ddl_runner.chain(CreateViewVisitor(connection=_ddl_runner.connection))

    @event.listens_for(metadata, "before_drop")
    def before_drop(target, connection, _ddl_runner=None, **kw):
        _ddl_runner.chain(DropViewVisitor(connection=_ddl_runner.connection))

    _hooked_metadatas.add(metadata)


class ViewClause(SchemaItem, TableClause, Visitable):
    __visit_name__ = "view"
    _view_select = None

    def __init__(self, *args, **kwargs):
        pass

    @property
    def key(self):
        if self.schema is None:
            return self.name
        return self.schema + "." + self.name

    def _init(self, name, metadata, selectable, **kwargs):
        super(ViewClause, self).__init__(quoted_name(name, kwargs.pop("quote", None)))
        self.metadata = metadata

        if metadata not in _hooked_metadatas:
            _register_views_hooks(metadata)

        self.schema = kwargs.pop("schema", metadata.schema)

        self.kwargs = kwargs
        self.indexes = set()
        self.constraints = set()
        self._columns = ColumnCollection()
        self.foreign_keys = set()
        self.foreign_key_constraints = set()
        self._extra_dependencies = set()
        if self.schema is not None:
            self.fullname = "%s.%s" % (self.schema, self.name)
        else:
            self.fullname = self.name

        self.comment = kwargs.pop("comment", None)

        for t in kwargs.pop("dependencies", []):
            if hasattr(t, "__table__"):
                self._extra_dependencies.add(t.__table__)
            else:
                self._extra_dependencies.add(t)

        if "info" in kwargs:
            self.info = kwargs.pop("info")
        if "listeners" in kwargs:
            listeners = kwargs.pop("listeners")
            for evt, fn in listeners:
                event.listen(self, evt, fn)

        self._prefixes = kwargs.pop("prefixes", [])

        self._view_select = selectable
        self.materialized = kwargs.pop("materialized", False)
        for c in self._view_select.c:
            # Simple reimplementation of _make_proxy. Ensures nothing useless
            # is kept from the selectable
            col = Column(c.name, c.type, key=c.key, primary_key=c.primary_key)

            col.table = self
            self._columns.add(col)
            if c.primary_key:
                self.primary_key.add(col)

        indexes = kwargs.pop("indexes", [])
        for index in indexes:
            index._set_parent(self)

    def __new__(cls, *args, **kw):
        if not args:
            # python3k pickle seems to call this
            return object.__new__(cls)

        try:
            name, metadata, args = args[0], args[1], args[2:]
        except IndexError:
            raise TypeError("Table() takes at least two arguments")

        schema = kw.get("schema", metadata.schema)

        table = object.__new__(cls)
        table.dispatch.before_parent_attach(table, metadata)
        metadata._add_table(name, schema, table)
        table._init(name, metadata, *args, **kw)
        table.dispatch.after_parent_attach(table, metadata)
        return table


class ViewMixin(object):
    __table_cls__ = ViewClause

    @classmethod
    def refresh(cls, session, concurrently=True):
        if not cls.__table__.materialized:
            raise Exception("only materialized views should be refreshed")
        session.flush()
        session.execute(RefreshMaterializedView(cls.__table__))
