from .tasks import make_celery
from .app import create_app
from .countries import load_data

app = create_app()
celery = make_celery(app)


load_data(app)
