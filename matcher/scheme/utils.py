import enum
import functools
import inspect
import itertools
from typing import Callable, List, Optional, Type

from matcher.exceptions import InvalidTransition
from sqlalchemy import column, event
from sqlalchemy.ext.compiler import compiles
from sqlalchemy.orm import Query, object_session
from sqlalchemy.schema import DDLElement
from sqlalchemy.sql import FromClause


class Transition(object):
    __slots__ = "name", "to_state", "from_states", "__doc__"

    def __init__(
        self, name: str, from_states: List[Optional[int]], to_state: int, doc: str = ""
    ) -> None:
        self.name = name
        self.to_state = to_state
        self.from_states = from_states
        self.__doc__ = str(doc)


class CustomEnum(enum.Enum):
    """A custom enum with serialization/deserialization methods"""

    def __str__(self):
        return self.name.lower()

    @classmethod
    def from_name(cls, name):
        return getattr(cls, str(name).upper(), None)

    @classmethod
    def coerce(cls, obj):
        if isinstance(obj, cls):
            return obj
        return cls.from_name(str(obj))

    @staticmethod
    def _gen_apply(transition):
        def apply(self, *args, **kwargs):
            return transition.apply(self, *args, **kwargs)

        apply.transition = transition
        apply.__doc__ = transition.__doc__
        return apply

    @staticmethod
    def _gen_can_apply(transition):
        @property
        def can_apply(self):
            return transition.can_apply(self)

        return can_apply

    @staticmethod
    def _gen_is_state(elem, field):
        @property
        def is_state(self):
            return getattr(self, field) == elem

        return is_state

    @classmethod
    def act_as_statemachine(cls, arg):
        """Create a state machine from this enum"""
        assert cls.__transitions__

        def wrapper(model):
            assert hasattr(model, field)

            # Discover the hooks defined by the @before and @after decorators
            hooks = {"before": [], "after": [], "after_save": []}
            for attr in dir(model):
                if not attr.startswith("__"):
                    hook = getattr(model, attr)
                    if isinstance(hook, Hook):
                        hooks[hook.hook_type].append(hook)

            # Re-order the hooks by order of definition using their order attribute
            for key in hooks:
                hooks[key] = sorted(hooks[key])

            def listener(mapper, connection, target):
                while target._state_machine_save_queue:
                    target._state_machine_save_queue.pop(0)()

            event.listens_for(model, "after_insert")(listener)
            event.listens_for(model, "after_update")(listener)

            # Save the name of the field, the enum base class and the hook list inside the class
            setattr(model, "_state_machine_field", field)
            setattr(model, "_state_machine_hooks", hooks)
            setattr(model, "_state_machine_save_queue", [])

            # Generate the `obj.{transition}()` methods
            for transition in cls.__transitions__:
                transition = BoundTransition(transition, cls)
                setattr(model, transition.name, cls._gen_apply(transition))
                setattr(
                    model,
                    "can_{name}".format(name=transition.name),
                    cls._gen_can_apply(transition),
                )

            # Generate the `is_{state}` properties
            for elem in cls:
                setattr(
                    model,
                    "is_{name}".format(name=str(elem)),
                    cls._gen_is_state(elem, field),
                )

            return model

        if inspect.isclass(arg):
            field = "state"
            return wrapper(arg)

        field = arg
        return wrapper


class BoundTransition(object):
    __slots__ = "name", "to_state", "from_states", "__doc__"

    def __init__(self, transition: Transition, enum: Type[CustomEnum]) -> None:
        self.__doc__ = transition.__doc__
        self.name = transition.name
        self.to_state = enum(transition.to_state)
        self.from_states = [
            None if state is None else enum(state) for state in transition.from_states
        ]

    def apply(self, model, *args, **kwargs):
        current_state = getattr(model, model._state_machine_field)

        if not self.can_apply(model):
            raise InvalidTransition(current_state, self.to_state)

        for hook in self.hook_list(model, "before"):
            hook(model, *args, **kwargs)

        setattr(model, model._state_machine_field, self.to_state)

        for hook in self.hook_list(model, "after"):
            hook(model, *args, **kwargs)

        for hook in self.hook_list(model, "after_save"):
            bound_hook = functools.partial(hook, model, *args, **kwargs)
            model._state_machine_save_queue.append(bound_hook)

        return model

    def can_apply(self, model) -> bool:
        current_state = getattr(model, model._state_machine_field)

        return current_state in self.from_states

    def hook_list(self, model, hook_type):
        hooks = model._state_machine_hooks[hook_type]

        for hook in hooks:
            if hook.transition == self.name or hook.transition is None:
                yield hook


# Counter used to get the order of definition
_hook_counter = itertools.count()


class Hook(object):
    def __init__(
        self,
        hook_type: str,
        transition: Transition,
        func: Callable[..., Optional[bool]],
    ) -> None:
        self.hook_type = hook_type
        self.transition = transition
        self.func = func
        self.order = next(_hook_counter)

    # Implement ordering
    def __lt__(self, other):
        return self.order.__lt__(other.order)

    def __call__(self, *args, **kwargs) -> None:
        result = self.func(*args, **kwargs)
        if result is False:
            # TODO: custom exception
            raise Exception("{} hook failed".format(self.hook_type))


def before(arg):
    if callable(arg):
        transition = None
        func = arg
        return Hook("before", transition, func)
    else:
        transition = arg

        def decorator(func):
            return Hook("before", transition, func)

        return decorator


def after(arg):
    if callable(arg):
        name = None
        func = arg
        return Hook("after", name, func)
    else:
        name = arg

        def decorator(func):
            return Hook("after", arg, func)

        return decorator


def after_save(arg):
    if callable(arg):
        name = None
        func = arg
        return Hook("after_save", name, func)
    else:
        name = arg

        def decorator(func):
            return Hook("after_save", arg, func)

        return decorator


class CreateExtension(DDLElement):
    __visit_name__ = "create_extension"

    def __init__(self, name):
        self.name = name


@compiles(CreateExtension, "postgresql")
def visit_create_extension(element, compiler, **kw):
    return "CREATE EXTENSION IF NOT EXISTS {name}".format(name=element.name)


def ensure_extension(name, metadata):
    CreateExtension(name).execute_at("before_create", metadata)


def inject_session(f):
    """Inject the session as parameters from object_session if not present"""

    def wrap(self, *args, session=None, **kwargs):
        if session is None:
            session = object_session(self)

        assert session is not None, "cannot continue without session"
        kwargs["session"] = session
        return f(self, *args, **kwargs)

    return wrap


# Borrowed from https://github.com/makmanalp/sqlalchemy-crosstab-postgresql/blob/master/crosstab.py
class crosstab(FromClause):
    def __init__(self, stmt, return_def, categories=None, auto_order=True):
        if not (isinstance(return_def, (list, tuple)) or return_def.is_selectable):
            raise TypeError("return_def must be a selectable or tuple/list")
        self.stmt = stmt
        self.columns = (
            return_def if isinstance(return_def, (list, tuple)) else return_def.columns
        )
        self.categories = categories
        if hasattr(return_def, "name"):
            self.name = return_def.name
        else:
            self.name = None

        if isinstance(self.stmt, Query):
            self.stmt = self.stmt.selectable
        if isinstance(self.categories, Query):
            self.categories = self.categories.selectable

        # Don't rely on the user to order their stuff
        if auto_order:
            self.stmt = self.stmt.order_by("1,2")
            if self.categories is not None:
                self.categories = self.categories.order_by("1")

    def _populate_column_collection(self):
        self._columns.update(column(name, type=type_) for name, type_ in self.names)


@compiles(crosstab, "postgresql")
def visit_element(element, compiler, **kw):
    # FIXME: literal binds are used here because I can't figure out how to bind
    # new parameters to the compiler
    stmt = element.stmt.compile(compiler, compile_kwargs={"literal_binds": True}).string
    if element.categories is not None:
        categories = element.categories.compile(
            compiler, compile_kwargs={"literal_binds": True}
        ).string
        return """crosstab($$%s$$, $$%s$$) AS (%s)""" % (
            stmt,
            categories,
            ", ".join(
                '"%s" %s' % (c.name, compiler.visit_typeclause(c)) for c in element.c
            ),
        )
    else:
        return """crosstab($$%s$$) AS (%s)""" % (
            stmt,
            ", ".join(
                "%s %s" % (c.name, compiler.visit_typeclause(c)) for c in element.c
            ),
        )
