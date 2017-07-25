import json
from flask import redirect, request
from flask.views import View
from restless.fl import FlaskResource
from restless.preparers import CollectionSubPreparer

from .. import db
from .utils import AutoPreparer
from ..scheme import ExternalObject, Scrap, Job
from ..scheme.queue import JobStatus


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
        scrap = Scrap.query.filter(Scrap.id == data['scrap']).one()
        job = Job()
        job.scrap = scrap
        job.status = JobStatus.SCHEDULED
        job.platform = scrap.platform
        job.data = dict(data)
        db.session.add(job)
        db.session.commit()
        return json.dumps({
            'job': job.self_link,
        })
