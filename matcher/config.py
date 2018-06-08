import os

from sqlalchemy.engine.url import URL


def env_var(key, default=None):
    if key + '_FILE' in os.environ:
        with open(os.environ[key + '_FILE'], 'r') as file:
            value = file.read().strip()
    elif key in os.environ:
        value = os.environ[key]
    else:
        value = default

    if str(value).upper() == 'TRUE':
        value = True
    elif str(value).upper() == 'FALSE':
        value = False

    return value


postgres_url = str(URL(
    drivername='postgres+psycopg2',
    host=env_var('POSTGRES_HOST', 'localhost'),
    port=env_var('POSTGRES_PORT', '5432'),
    username=env_var('POSTGRES_USERNAME'),
    password=env_var('POSTGRES_PASSWORD'),
    database=env_var('POSTGRES_DATABASE', 'matcher'),
))


class Config(object):
    DEBUG = env_var('DEBUG', True)
    TESTING = False
    BASE_DIR = os.path.abspath(os.path.dirname(__file__))

    SQLALCHEMY_DATABASE_URI = env_var('SQLALCHEMY_DATABASE_URI', postgres_url)
    SQLALCHEMY_TRACK_MODIFICATIONS = True
    DATABASE_CONNECT_OPTIONS = {}

    THREADS_PER_PAGE = 2
    SECRET_KEY = env_var('SECRET_KEY',
                         'Something reeaaally secret (wow, spooky.)')
