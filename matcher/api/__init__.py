from flask import Blueprint

from ..scheme.object import ExternalObject
from ..scheme.platform import Platform, PlatformGroup, Scrap
from ..scheme.value import Value
from .index import IndexView
from .object import ObjectResource
from .platform import PlatformGroupResource, PlatformResource, ScrapResource
from .value import ValueResource

api = Blueprint('api', __name__)

Platform.register_api(api, 'platforms', PlatformResource)
PlatformGroup.register_api(api, 'groups', PlatformGroupResource)
Scrap.register_api(api, 'scraps', ScrapResource)
Value.register_api(api, 'values', ValueResource)
ExternalObject.register_api(api, 'objects', ObjectResource)

api.add_url_rule('/', view_func=IndexView.as_view('index'))


def setup_api(app):
    app.register_blueprint(api, url_prefix='/api')
