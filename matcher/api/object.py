from flask import request

import restless.exceptions
from matcher.app import db
from matcher.scheme.object import ExternalObject
from matcher.scheme.platform import Scrap
from restless.preparers import (CollectionSubPreparer, FieldsPreparer,
                                SubPreparer,)
from sqlalchemy.orm.exc import NoResultFound

from .utils import AutoPreparer, CustomFlaskResource


class ObjectResource(CustomFlaskResource):
    preparer = AutoPreparer({
        'type': 'type',
        'attributes': CollectionSubPreparer('attributes', AutoPreparer({
            'type': 'type',
            'text': 'text',
            'score': 'score',
        })),
        'links': CollectionSubPreparer('links', FieldsPreparer(fields={
            'external_id': 'external_id',
            'platform': SubPreparer('platform', AutoPreparer({
                'name': 'name',
                'slug': 'slug'
            }))
        }))
    })

    def is_authenticated(self):
        return True

    def list(self):
        return db.session.query(ExternalObject).all()

    def detail(self, pk):
        return db.session.query(ExternalObject).filter(ExternalObject.id == pk).one()

    def create(self):
        scrap_id = request.headers.get('x-scrap-id', None)
        if scrap_id is None:
            raise restless.exceptions.\
                BadRequest('Missing `x-scrap-id` header')

        try:
            scrap = db.session.query(Scrap).filter(Scrap.id == scrap_id).one()
        except NoResultFound:
            raise restless.exceptions.NotFound('Scrap not found')

        data = ExternalObject.normalize_dict(self.data)

        # FIXME: kinda ugly workaround
        if data['type'] is None and self.data['type'] != 'any':
            raise restless.exceptions.BadRequest('Field "type" is required')

        if data['relation'] is not None:
            raise restless.exceptions.BadRequest(
                'Field "relation" is not allowed on the root object')

        obj = ExternalObject.insert_dict(data, scrap)

        return obj
