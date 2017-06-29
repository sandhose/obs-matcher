from restless.fl import FlaskResource
from restless.preparers import FieldsPreparer, SubPreparer, \
    CollectionSubPreparer

from .utils import AutoPreparer
from ..scheme import Value
from .. import db


class ValueResource(FlaskResource):
    preparer = AutoPreparer({
        'type': 'type.__str__',
        'external_object': SubPreparer('external_object', AutoPreparer({
            'type': 'type.__str__',
        })),
        'text': 'text',
        'score': 'score',
        'sources': CollectionSubPreparer('sources', FieldsPreparer(fields={
            'platform': SubPreparer('platform', AutoPreparer({
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
