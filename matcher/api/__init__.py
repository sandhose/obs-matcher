from flask import request, Blueprint

from ..scheme import Platform, PlatformGroup, Scrap, Value, Job
from .platform import PlatformGroupResource, PlatformResource, ScrapResource
from .value import ValueResource
from .queue import JobResource

api = Blueprint('api', __name__)

Platform.register_api(api, 'platforms', PlatformResource)
PlatformGroup.register_api(api, 'groups', PlatformGroupResource)
Scrap.register_api(api, 'scraps', ScrapResource)
Job.register_api(api, 'jobs', JobResource)

Value.register_api(api, 'values', ValueResource)


@api.route('/api/objects/', methods=['POST'])
def objects():
    data = request.get_json()
    print('got a {} from scrap {}'.format(data['type'], data['scrap']))
    return 'yeay.'


def setup_api(app):
    app.register_blueprint(api, url_prefix='/api')
