import fcntl
import functools
import itertools
import logging
from contextlib import contextmanager
from pathlib import Path
from typing import Callable, Optional, Tuple

from flask import current_app, template_rendered
from sqlalchemy import desc

logger = logging.getLogger(__name__)


class TaskFormatter(logging.Formatter):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        try:
            from celery._state import get_current_task

            self.get_current_task = get_current_task
        except ImportError:
            self.get_current_task = lambda: None

    def format(self, record):
        task = self.get_current_task()
        if task and task.request:
            record.__dict__.update(task_id=task.request.id, task_name=task.name)
        else:
            record.__dict__.setdefault("task_name", "")
            record.__dict__.setdefault("task_id", "")

        return super().format(record)


def trace(logger):
    logger = logger.getChild("trace")

    def wrapper(func):
        @functools.wraps(func)
        def wrapped(*args, **kwargs):
            result = func(*args, **kwargs)
            parameters = ", ".join(
                itertools.chain(
                    (repr(arg) for arg in args),
                    ("%s=%r" % (key, value) for (key, value) in kwargs.items()),
                )
            )

            logger.debug("%s(%s) = %r", func.__name__, parameters, result)
            return result

        return wrapped

    return wrapper


@contextmanager
def captured_templates(app):
    """Capture rendered templates, useful for testing"""
    recorded = []

    def record(sender, template, context, **extra):
        recorded.append((template, context))

    template_rendered.connect(record, app)
    try:
        yield recorded
    finally:
        template_rendered.disconnect(record, app)


class Lock:
    def __init__(self, name: str) -> None:
        self.name = name
        self._fd = None

    @property
    def fd(self):
        if self._fd is None:
            self._fd = current_app.open_instance_resource(self.name + ".lock", "w")

        return self._fd

    def __enter__(self):
        logging.debug("Locking %s", self.name)
        if not current_app.config["BYPASS_LOCKS"]:
            fcntl.lockf(self.fd, fcntl.LOCK_EX)

    def __exit__(self, *args):
        logging.debug("Unlocking %s", self.name)
        if not current_app.config["BYPASS_LOCKS"]:
            fcntl.lockf(self.fd, fcntl.LOCK_UN)


def _data_path(prefix: str) -> Callable[[], Path]:
    parent_created = False

    def p():
        # This needs to be a callable because the current_app might not be configured at this time
        nonlocal parent_created
        path = Path(current_app.config["DATA_DIR"]) / prefix

        if not parent_created:
            path.mkdir(parents=True, exist_ok=True)
            parent_created = True

        return path

    return p


export_path = _data_path("exports")
import_path = _data_path("imports")


def parse_ordering(ordering: Optional[str]) -> Tuple[Optional[str], Optional[str]]:
    if not ordering:
        return (None, None)

    [key, direction] = ordering.rsplit("-", 1)
    return (key, direction)


def apply_ordering(order_map, query, key=None, direction="asc"):
    col = order_map.get(key, None)
    if col is None:
        return query
    print(col)

    if direction == "desc":
        col = desc(col)

    return query.order_by(col)
