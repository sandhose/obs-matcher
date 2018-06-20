from flask_restplus import Namespace, abort
from flask import request

from matcher.scheme.platform import Scrap
from ..resources import DbResource, CeleryResource
from .. import models

api = Namespace('queue', description='Queue new objects and inspect the current state of it')


api.models[models.queue.name] = models.queue


@api.route('/')
class Queue(DbResource, CeleryResource):
    """Queue new object and inspect the queue"""

    @api.doc('inspect_queue')
    @api.marshal_with(models.queue)
    def get(self):
        """Inspect the queue"""
        # FIXME: currently bare bone
        return {
            'workers': [host for node in self.celery.control.ping() for host in node]
        }

    @api.doc('queue_object')
    def post(self):
        """Queue a new object for insertion"""
        # FIXME: works but is quite ugly

        scrap_id = request.headers.get('x-scrap-id', None)
        if scrap_id is None:
            abort(400, 'Missing x-scrap-id header')
        scrap_id = int(scrap_id)

        assert self.session.query(Scrap).get(scrap_id)

        self.celery.send_task('matcher.tasks.object.insert_dict', [request.json, scrap_id])
        return {'status': 'queued'}
