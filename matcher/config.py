import os

# FIXME: instance config file


class Config(object):
    DEBUG = False
    TESTING = False
    BASE_DIR = os.path.abspath(os.path.dirname(__file__))

    SQLALCHEMY_DATABASE_URI = 'postgresql+psycopg2://localhost/matcher'
    SQLALCHEMY_TRACK_MODIFICATIONS = True
    DATABASE_CONNECT_OPTIONS = {}

    THREADS_PER_PAGE = 2
    SECRET_KEY = 'Something reeaaally secret (wow, spooky.)'


class ProductionConfig(Config):
    pass


class TestingConfig(Config):
    TESTING = True
    SQLALCHEMY_DATABASE_URI = 'postgresql+psycopg2://localhost/matcher-test'


class DevelopmentConfig(Config):
    DEBUG = True
