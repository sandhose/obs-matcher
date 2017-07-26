import json
from flask import request
from flask.views import View
from restless.fl import FlaskResource
from restless.preparers import CollectionSubPreparer

from .utils import AutoPreparer
from ..scheme import ExternalObject


class ObjectResource(FlaskResource):
    preparer = AutoPreparer({
        'type': 'type.__str__',
        'attributes': CollectionSubPreparer('attributes', AutoPreparer({
            'type': 'type.__str__',
            'text': 'text',
            'score': 'score',
        })),
    })

    def is_authenticated(self):
        return True

    def list(self):
        return ExternalObject.query.all()

    def detail(self, pk):
        return ExternalObject.query.filter(ExternalObject.id == pk).one()


class ObjectCreate(View):
    methods = ['POST']

    def dispatch_request(self):
        data = request.get_json()
        return json.dumps(data)
