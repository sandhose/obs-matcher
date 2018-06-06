from restless.preparers import (CollectionSubPreparer, FieldsPreparer,
                                SubPreparer,)

from ..scheme.value import Value
from .utils import AutoPreparer, CustomFlaskResource


class ValueResource(CustomFlaskResource):
    preparer = AutoPreparer({
        'type': 'type',
        'external_object': SubPreparer('external_object', AutoPreparer({
            'type': 'type',
        })),
        'text': 'text',
        'score': 'score',
        'sources': CollectionSubPreparer(
            'value_sources',
            FieldsPreparer(fields={
                'platform': SubPreparer('platform', AutoPreparer({
                    'name': 'name',
                })),
                'score': 'score',
                'score_factor': 'score_factor',
            })
        ),
    })

    def is_authenticated(self):
        return True

    def list(self):
        return Value.query.all()

    def detail(self, pk):
        return Value.query.filter(Value.id == pk).one()
