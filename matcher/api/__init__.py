from flask import Blueprint

from flask_restplus import Api

from .errors import install_error_handlers
from .namespaces import register_all

blueprint = Blueprint('api_v2', __name__)
api = Api(blueprint, version='1.0', title='Matcher API')

install_error_handlers(blueprint, api)
register_all(api)
