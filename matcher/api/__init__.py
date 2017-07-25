from flask import request, Blueprint

from ..scheme import Platform, PlatformGroup, Scrap, Value, Job, ExternalObject
from .platform import PlatformGroupResource, PlatformResource, ScrapResource
from .value import ValueResource
from .queue import JobResource
from .object import ObjectResource, ObjectCreate
from .index import IndexView

api = Blueprint('api', __name__)

Platform.register_api(api, 'platforms', PlatformResource)
PlatformGroup.register_api(api, 'groups', PlatformGroupResource)
Scrap.register_api(api, 'scraps', ScrapResource)
Job.register_api(api, 'jobs', JobResource)
Value.register_api(api, 'values', ValueResource)

api.add_url_rule('/', view_func=IndexView.as_view('index'))
api.add_url_rule('/objects/', view_func=ObjectCreate.as_view('object_create'),
                 methods=['POST'])

ExternalObject.register_api(api, 'objects', ObjectResource)


@api.route('/test/', methods=['POST'])
def objects():
    data = request.get_json()
    print('got a {} from scrap {}'.format(data['type'], data['scrap']))
    return 'yeay.'


def setup_api(app):
    app.register_blueprint(api, url_prefix='/api')
