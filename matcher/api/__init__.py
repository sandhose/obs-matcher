from flask import request

from ..scheme import Platform, PlatformGroup, Scrap, ValueID, Value
from .platform import PlatformGroupResource, PlatformResource, ScrapResource
from .value import ValueIDResource, ValueResource


def setup_api(app):
    Platform.register_api(app, 'platforms/', PlatformResource)
    PlatformGroup.register_api(app, 'groups/', PlatformGroupResource)
    Scrap.register_api(app, 'scraps/', ScrapResource)

    ValueID.register_api(app, 'value_ids/', ValueIDResource)
    Value.register_api(app, 'values/', ValueResource)

    @app.route('/api/objects/', methods=['POST'])
    def objects():
        data = request.get_json()
        print('got a {} from scrap {}'.format(data['type'], data['scrap']))
        return 'yeay.'
