from restless.fl import FlaskResource
from restless.preparers import CollectionSubPreparer, SubPreparer

from .. import db
from .utils import AutoPreparer
from ..scheme.object import ExternalObject, ExternalObjectType


class ObjectResource(FlaskResource):
    preparer = AutoPreparer({
        'type': 'type.__str__',
        'attributes': CollectionSubPreparer('attributes', AutoPreparer({
            'type': 'type.__str__',
            'text': 'text',
            'score': 'score',
        })),
        'links': CollectionSubPreparer('links', AutoPreparer({
            'platform': SubPreparer('platform', AutoPreparer({
                'name': 'name',
                'slug': 'slug'
            }))
        }))
    })

    def is_authenticated(self):
        return True

    def list(self):
        return ExternalObject.query.all()

    def detail(self, pk):
        return ExternalObject.query.filter(ExternalObject.id == pk).one()

    def create(self):
        data = self.data

        obj = ExternalObject.lookup_or_create(
            obj_type=ExternalObjectType.from_name(data['type']),
            links=data['links'],
            session=db.session
        )
        db.session.commit()

        return obj
