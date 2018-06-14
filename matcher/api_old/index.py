from flask import jsonify, url_for
from flask.views import View


class IndexView(View):
    """A GET view that lists other endpoints"""

    methods = ['GET']
    apis = {}
    """dict containing a name => path mapping of the resources"""

    @classmethod
    def register_api(cls, name, path):
        """Called by the ResourceMixin when registering"""
        cls.apis[name] = path

    def dispatch_request(self):
        obj = map(
            lambda x: (x[0], url_for(x[1], _external=True)),
            self.apis.items()
        )
        return jsonify(dict(obj))
