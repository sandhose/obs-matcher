from flask import jsonify, url_for
from flask.views import View


class IndexView(View):
    methods = ['GET']
    apis = {}

    @classmethod
    def register_api(cls, name, path):
        cls.apis[name] = path

    def dispatch_request(self):
        obj = map(
            lambda x: (x[0], url_for(x[1], _external=True)),
            self.apis.items()
        )
        return jsonify(dict(obj))
