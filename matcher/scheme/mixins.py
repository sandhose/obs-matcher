from sqlalchemy.ext import compiler
from sqlalchemy.ext.declarative import declared_attr
from sqlalchemy.schema import DDLElement
from sqlalchemy.sql import table


class CreateView(DDLElement):
    def __init__(self, name, selectable, materialized=False):
        self.name = name
        self.selectable = selectable
        self.materialized = materialized


class DropView(DDLElement):
    def __init__(self, name, materialized=False):
        self.name = name
        self.materialized = materialized


@compiler.compiles(CreateView)
def compile_create_view(element, compiler, **kw):
    return "CREATE {type} {name} AS {selectable}".format(
        type=('MATERIALIZED VIEW' if element.materialized else 'VIEW'),
        name=element.name,
        selectable=compiler.sql_compiler.process(element.selectable)
    )


@compiler.compiles(DropView)
def compile_drop_view(element, compiler, **kw):
    return "DROP {type} {name}".format(
        type=('MATERIALIZED VIEW' if element.materialized else 'VIEW'),
        name=element.name,
    )


def view(name, metadata, selectable, materialized=False):
    t = table(name)

    for c in selectable.c:
        c._make_proxy(t)

    CreateView(name, selectable, materialized).execute_at('after-create', metadata)
    DropView(name, materialized).execute_at('before-drop', metadata)
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
