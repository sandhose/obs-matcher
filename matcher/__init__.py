from gevent.monkey import patch_all

patch_all()  # noqa: E702
from psycogreen.gevent import patch_psycopg

patch_psycopg()  # noqa: E702

from celery import Celery
from werkzeug.middleware.proxy_fix import ProxyFix

from .app import create_app, injector
from .countries import load_data

app = create_app()
celery = injector.get(Celery)

app.wsgi_app = ProxyFix(app.wsgi_app)

load_data(app)
