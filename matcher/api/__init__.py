from flask import Blueprint

from ..scheme import Platform, PlatformGroup, Scrap, Value, ExternalObject
from .platform import PlatformGroupResource, PlatformResource, ScrapResource
from .value import ValueResource
from .object import ObjectResource
from .index import IndexView

api = Blueprint('api', __name__)

Platform.register_api(api, 'platforms', PlatformResource)
PlatformGroup.register_api(api, 'groups', PlatformGroupResource)
Scrap.register_api(api, 'scraps', ScrapResource)
Value.register_api(api, 'values', ValueResource)
ExternalObject.register_api(api, 'objects', ObjectResource)

api.add_url_rule('/', view_func=IndexView.as_view('index'))


def setup_api(app):
    app.register_blueprint(api, url_prefix='/api')
