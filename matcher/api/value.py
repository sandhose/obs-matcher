import restless.exceptions
from restless.fl import FlaskResource
from restless.preparers import FieldsPreparer, SubPreparer, \
    CollectionSubPreparer

from ..scheme import Value
from .. import db


class ValueResource(FlaskResource):
    preparer = FieldsPreparer(fields={
        'id': 'id',
        'self': 'self_link',
        'type': 'type.__str__',
        'external_object': SubPreparer('external_object', FieldsPreparer(
            fields={
                'id': 'id',
                # 'self': 'self_link',
                'type': 'type.__str__',
            }
        )),
        'text': 'text',
        'score': 'score',
        'sources': CollectionSubPreparer('sources', FieldsPreparer(fields={
            'platform': SubPreparer('platform', FieldsPreparer(fields={
                'id': 'id',
                'self': 'self_link',
                'name': 'name',
            })),
            'score': 'score',
            'score_factor': 'score_factor',
        })),
    })

    def is_authenticated(self):
        return True

    def list(self):
        return Value.query.all()

    def create(self):
        value = Value(**self.data)
        db.session.add(value)
        db.session.commit()
        return value
