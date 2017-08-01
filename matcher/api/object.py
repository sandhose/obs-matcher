import itertools
from restless.fl import FlaskResource
from restless.preparers import CollectionSubPreparer, SubPreparer, \
    FieldsPreparer

from .. import db
from .utils import AutoPreparer
from ..scheme.object import ExternalObject, ExternalObjectType
from ..scheme.platform import Platform


class ObjectResource(FlaskResource):
    preparer = AutoPreparer({
        'type': 'type.__str__',
        'attributes': CollectionSubPreparer('attributes', AutoPreparer({
            'type': 'type.__str__',
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
        return ExternalObject.query.all()

    def detail(self, pk):
        return ExternalObject.query.filter(ExternalObject.id == pk).one()

    def create(self):
        data = self.data

        obj = ExternalObject.lookup_or_create(
            obj_type=ExternalObjectType.from_name(data['type']),
            links=data['links'],
        )

        # FIXME: this is ugly
        def map_attributes(type, attrs):
            if not isinstance(attrs, list):
                attrs = [attrs]
            return [{'type': type, **attr} for attr in attrs]

        attributes = itertools.chain.from_iterable(
            [map_attributes(t, a)
             for t, a in data['attributes'].items()])

        # FIXME: get platform from scrap
        obj.add_attributes(attributes, Platform.lookup('rakutentv'))

        db.session.add(obj)
        db.session.commit()

        return obj
