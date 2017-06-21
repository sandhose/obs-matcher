from restless.fl import FlaskResource
from restless.preparers import FieldsPreparer, SubPreparer, \
        CollectionSubPreparer

from ..scheme import Value


class ValueResource(FlaskResource):
    preparer = FieldsPreparer(fields={
        'id': 'id',
        'self': 'self_link',
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
        'value_id': SubPreparer('value_id', FieldsPreparer(fields={
            'id': 'id',
            'self': 'self_link',
            'type': 'type',
            'object': 'object_id',
        })),
    })

    def list(self):
        return Value.query.all()
