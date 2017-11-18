from .app import create_app
from .countries import load_data
app = create_app()

load_data(app)
