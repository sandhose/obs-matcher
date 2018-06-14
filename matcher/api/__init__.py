from flask import Blueprint
from flask_restplus import Api

from . import platforms

blueprint = Blueprint('api_v2', __name__)
api = Api(blueprint, version='1.0', title='Matcher API')

api.add_namespace(platforms.api)
