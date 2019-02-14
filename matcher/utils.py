import fcntl
from pathlib import Path
from typing import Callable, Optional, Tuple

from flask import current_app
from sqlalchemy import desc


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
        if not current_app.config["BYPASS_LOCKS"]:
            fcntl.lockf(self.fd, fcntl.LOCK_EX)

    def __exit__(self, *args):
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
