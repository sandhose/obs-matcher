from flask import Blueprint

from flask_restplus import Api

from .namespaces import register_all

blueprint = Blueprint('api_v2', __name__)
api = Api(blueprint, version='1.0', title='Matcher API')

register_all(api)
