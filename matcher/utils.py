import fcntl
import os

bypass = bool(os.environ.get('BYPASS_LOCKS', None))


class Lock():
    def __init__(self, name):
        self.name = name
        self._fd = None

    @property
    def fd(self):
        from flask import current_app
        if self._fd is None:
            self._fd = current_app.open_instance_resource(self.name + '.lock', 'w')

        return self._fd

    def __enter__(self):
        if not bypass:
            fcntl.lockf(self.fd, fcntl.LOCK_EX)

    def __exit__(self, *args):
        if not bypass:
            fcntl.lockf(self.fd, fcntl.LOCK_UN)
