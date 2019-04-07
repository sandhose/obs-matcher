from gevent.monkey import patch_all

patch_all()
from psycogreen.gevent import patch_psycopg  # noqa: E402

patch_psycopg()

from werkzeug.contrib.fixers import ProxyFix  # noqa: E402
from celery import Celery  # noqa: E402

from .app import create_app, injector  # noqa: E402
from .countries import load_data  # noqa: E402


app = create_app()
celery = injector.get(Celery)

app.wsgi_app = ProxyFix(app.wsgi_app)


load_data(app)
