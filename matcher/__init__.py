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


load_data(app)
