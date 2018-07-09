from sqlalchemy import event
from sqlalchemy.ext import compiler
from sqlalchemy.ext.declarative import declared_attr
from sqlalchemy.schema import DDLElement
from sqlalchemy.sql import table


class CreateView(DDLElement):
    __visit_name__ = "create_view"

    def __init__(self, name, selectable, materialized=False):
        self.name = name
        self.selectable = selectable
        self.materialized = materialized


class DropView(DDLElement):
    __visit_name__ = "drop_view"

    def __init__(self, name, materialized=False):
        self.name = name
        self.materialized = materialized


@compiler.compiles(CreateView)
def compile_create_view(element, compiler, **kw):
    return "CREATE OR REPLACE {type} {name} AS {selectable}".format(
        type=('MATERIALIZED VIEW' if element.materialized else 'VIEW'),
        name=element.name,
        selectable=compiler.sql_compiler.process(element.selectable)
    )


@compiler.compiles(DropView)
def compile_drop_view(element, compiler, **kw):
    return "DROP {type} IF EXISTS {name}".format(
        type=('MATERIALIZED VIEW' if element.materialized else 'VIEW'),
        name=element.name,
    )


_views_registry = {}


def _register_views_hooks(metadata):
    # This creates hooks to create and drop in the right order.
    # The views are created in the order they were declared, and dropped in the reversed order.
    drop_views = []
    create_views = []

    @event.listens_for(metadata, 'after_create')
    def after_create(target, connection, **kw):
        for ddl in create_views:
            connection.execute(ddl)

    @event.listens_for(metadata, 'before_drop')
    def before_drop(target, connection, **kw):
        for ddl in reversed(drop_views):
            connection.execute(ddl)

    return dict(drop=drop_views, create=create_views)


def view(name, metadata, selectable, materialized=False):
    t = table(name)

    for c in selectable.c:
        c._make_proxy(t)

    if metadata not in _views_registry:
        _views_registry[metadata] = _register_views_hooks(metadata)

    _views_registry[metadata]['create'].append(CreateView(name, selectable, materialized))
    _views_registry[metadata]['drop'].append(DropView(name, materialized))
    return t


class ViewMixin(object):
    __materialized__ = False

    @declared_attr
    def __table__(cls):
        if not hasattr(cls, '__selectable__'):
            raise Exception("need selectable")

        return view(cls.__tablename__, cls.metadata, cls.__selectable__, cls.__materialized__)

    @classmethod
    def refresh(cls, session, concurrently=True):
        if not cls.__materialized__:
            raise Exception('only materialized views should be refreshed')
        session.flush()
        session.execute('REFRESH MATERIALIZED VIEW{opts} {name}'
                        .format(opts=('CONCURRENTLY' if concurrently else ''),
                                name=cls.__table__.fullname))
