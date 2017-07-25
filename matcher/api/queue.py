from flask import jsonify
from flask.views import View
from restless.fl import FlaskResource
from restless.preparers import SubPreparer

from .utils import AutoPreparer
from ..scheme import Job, Platform
from ..scheme.queue import JobStatus
from ..scheme.object import ExternalObjectType


class JobResource(FlaskResource):
    preparer = AutoPreparer({
        'platform': SubPreparer('platform', AutoPreparer({
            'name': 'name',
        })),
        'scrap': SubPreparer('scrap', AutoPreparer({
            'date': 'date',
        })),
        'type': 'type.__str__',
        'data': 'data',
        'status': 'status.__str__',
    })

    def is_authenticated(self):
        return True

    def list(self):
        q = Job.query
        args = self.request.args

        if 'status' in args:
            q = q.filter(Job.status == JobStatus.from_name(args['status']))

        if 'type' in args:
            q = q.filter(
                Job.type == ExternalObjectType.from_name(args['type']))

        if 'platform' in args:
            q = q.filter(Job.platform == Platform.resolve(args['platform']))

        return q.all()

    def detail(self, pk):
        return Job.query.filter(Job.id == pk).one()
