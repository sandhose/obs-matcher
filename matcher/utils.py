import fcntl
import contextlib

f = open('/tmp/testlock', 'w')


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
        fcntl.lockf(self.fd, fcntl.LOCK_EX)

    def __exit__(self, *args):
        fcntl.lockf(self.fd, fcntl.LOCK_UN)


@contextlib.contextmanager
def applock(app, name):
    fcntl.lockf(f, fcntl.LOCK_EX)

    yield

    fcntl.lockf(f, fcntl.LOCK_UN)
