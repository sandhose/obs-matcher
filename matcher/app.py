import os
from flask import Flask
from flask_migrate import Migrate
from flask_sqlalchemy import SQLAlchemy

app = Flask('matcher')

# Load config using environment variable
env = os.environ.get('OBS_ENV', 'development')
app.config.from_object('matcher.config.{}Config'.format(env.title()))

db = SQLAlchemy(app)

migrate = Migrate(app=app, db=db,
                  directory=os.path.join(os.path.dirname(__file__),
                                         'migrations'))
