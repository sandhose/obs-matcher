import os
from pathlib import Path

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

postgres_test_url = str(URL(
    drivername='postgres+psycopg2',
    host=env_var('POSTGRES_TEST_HOST', env_var('POSTGRES_HOST', 'localhost')),
    port=env_var('POSTGRES_TEST_PORT', env_var('POSTGRES_PORT', '5432')),
    username=env_var('POSTGRES_TEST_USERNAME', env_var('POSTGRES_USERNAME')),
    password=env_var('POSTGRES_TEST_PASSWORD', env_var('POSTGRES_PASSWORD')),
    database=env_var('POSTGRES_TEST_DATABASE', env_var('POSTGRES_DATABASE', 'matcher')),
))

redis_url = str(URL(
    drivername='redis',
    host=env_var('REDIS_HOST', 'localhost'),
    port=env_var('REDIS_PORT', '6379'),
    username=env_var('REDIS_USERNAME'),
    password=env_var('REDIS_PASSWORD'),
    database=env_var('REDIS_DATABASE'),
))


class Config(object):
    DEBUG = env_var('DEBUG', True)
    TESTING = False
    BASE_DIR = os.path.abspath(os.path.dirname(__file__))

    SQLALCHEMY_DATABASE_URI = env_var('SQLALCHEMY_DATABASE_URI', postgres_url)
    SQLALCHEMY_TRACK_MODIFICATIONS = True

    CELERY_BROKER_URL = env_var('CELERY_BROKER_URL', redis_url)
    CELERY_RESULT_BACKEND = env_var('CELERY_RESULT_BACKEND', redis_url)

    THREADS_PER_PAGE = 2
    SECRET_KEY = env_var('SECRET_KEY',
                         'Something reeaaally secret (wow, spooky.)')

    DATA_DIR = Path(env_var('DATA_DIR', BASE_DIR + '/data'))
    BYPASS_LOCKS = env_var('BYPASS_LOCKS', False)


class TestConfig(Config):
    SQLALCHEMY_DATABASE_URI = env_var('SQLALCHEMY_TEST_DATABASE_URI', postgres_test_url)
    TESTING = True
