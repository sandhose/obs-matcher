import fcntl
import os
from pathlib import Path

from flask import current_app

bypass = bool(os.environ.get('BYPASS_LOCKS', None))


class Lock():
    def __init__(self, name):
        self.name = name
        self._fd = None

    @property
    def fd(self):
        if self._fd is None:
            self._fd = current_app.open_instance_resource(self.name + '.lock', 'w')

        return self._fd

    def __enter__(self):
        if not bypass:
            fcntl.lockf(self.fd, fcntl.LOCK_EX)

    def __exit__(self, *args):
        if not bypass:
            fcntl.lockf(self.fd, fcntl.LOCK_UN)


def open_export(path, *args, **kwargs):
    prefix = Path(current_app.config['EXPORTS_LOCATION'])
    path = prefix / path
    path.parent.mkdir(parents=True, exist_ok=True)
    return path.open(*args, **kwargs)
