import enum

from sqlalchemy import column
from sqlalchemy.ext.compiler import compiles
from sqlalchemy.orm import Query, object_session
from sqlalchemy.schema import DDLElement
from sqlalchemy.sql import FromClause


class CustomEnum(enum.Enum):
    """A custom enum with serialization/deserialization methods"""

    def __str__(self):
        return self.name.lower()

    @classmethod
    def from_name(cls, name):
        if name is None:
            return None
        return getattr(cls, name.upper(), None)


class CreateExtension(DDLElement):
    __visit_name__ = 'create_extension'

    def __init__(self, name):
        self.name = name


@compiles(CreateExtension, 'postgresql')
def visit_create_extension(element, compiler, **kw):
    return 'CREATE EXTENSION IF NOT EXISTS {name}'.format(name=element.name)


def ensure_extension(name, metadata):
    CreateExtension(name).execute_at('before_create', metadata)


def inject_session(f):
    """Inject the session as parameters from object_session if not present"""

    def wrap(self, *args, session=None, **kwargs):
        if session is None:
            session = object_session(self)

        assert session is not None, "cannot continue without session"
        kwargs['session'] = session
        return f(self, *args, **kwargs)
    return wrap


# Borrowed from https://github.com/makmanalp/sqlalchemy-crosstab-postgresql/blob/master/crosstab.py
class crosstab(FromClause):
    def __init__(self, stmt, return_def, categories=None, auto_order=True):
        if not (isinstance(return_def, (list, tuple)) or return_def.is_selectable):
            raise TypeError('return_def must be a selectable or tuple/list')
        self.stmt = stmt
        self.columns = return_def if isinstance(return_def, (list, tuple)) \
            else return_def.columns
        self.categories = categories
        if hasattr(return_def, 'name'):
            self.name = return_def.name
        else:
            self.name = None

        if isinstance(self.stmt, Query):
            self.stmt = self.stmt.selectable
        if isinstance(self.categories, Query):
            self.categories = self.categories.selectable

        # Don't rely on the user to order their stuff
        if auto_order:
            self.stmt = self.stmt.order_by('1,2')
            if self.categories is not None:
                self.categories = self.categories.order_by('1')

    def _populate_column_collection(self):
        self._columns.update(
            column(name, type=type_)
            for name, type_ in self.names
        )


@compiles(crosstab, 'postgresql')
def visit_element(element, compiler, **kw):
    # FIXME: literal binds are used here because I can't figure out how to bind
    # new parameters to the compiler
    stmt = element.stmt.compile(compiler,
                                compile_kwargs={"literal_binds": True}).string
    if element.categories is not None:
        categories = element.categories.compile(compiler,
                                                compile_kwargs={"literal_binds": True}).string
        return """crosstab($$%s$$, $$%s$$) AS (%s)""" % (
            stmt,
            categories,
            ", ".join(
                "\"%s\" %s" % (c.name, compiler.visit_typeclause(c))
                for c in element.c
            )
        )
    else:
        return """crosstab($$%s$$) AS (%s)""" % (
            stmt,
            ", ".join(
                "%s %s" % (c.name, compiler.visit_typeclause(c))
                for c in element.c
            )
        )
