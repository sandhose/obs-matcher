from gevent.monkey import patch_all
patch_all()
from psycogreen.gevent import patch_psycopg
patch_psycopg()

from werkzeug.contrib.fixers import ProxyFix
from celery import Celery

from .app import create_app, injector
from .countries import load_data


app = create_app()
celery = injector.get(Celery)

app.wsgi_app = ProxyFix(app.wsgi_app)

# FIXME: This is needed to discover tasks
import matcher.tasks.object  # noqa
import matcher.tasks.export  # noqa
import matcher.tasks.import_  # noqa


load_data(app)
