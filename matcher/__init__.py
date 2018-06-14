from werkzeug.contrib.fixers import ProxyFix

from .app import create_app
from .countries import load_data
from .tasks import make_celery

app = create_app()
celery = make_celery(app)

app.wsgi_app = ProxyFix(app.wsgi_app)

# FIXME: This is needed to discover tasks
import matcher.tasks.object  # noqa


load_data(app)
