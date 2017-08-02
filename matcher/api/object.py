import itertools
import restless.exceptions
from sqlalchemy.orm.exc import NoResultFound
from restless.fl import FlaskResource
from restless.preparers import CollectionSubPreparer, SubPreparer, \
    FieldsPreparer

from .. import db
from .utils import AutoPreparer
from ..scheme.object import ExternalObject, ExternalObjectType, \
    AmbiguousLinkError, ObjectTypeMismatchError, ExternalIDMismatchError
from ..scheme.platform import Scrap


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

        try:
            scrap = Scrap.query.filter(Scrap.id == data['scrap']).one()
        except KeyError:
            raise restless.exceptions.BadRequest('Missing key `scrap`')
        except NoResultFound:
            raise restless.exceptions.NotFound('Scrap not found')

        try:
            obj = ExternalObject.lookup_or_create(
                obj_type=ExternalObjectType.from_name(data['type']),
                links=data['links'],
            )
        except AmbiguousLinkError:
            raise restless.exceptions.Unavailable(
                'ambiguous link. Merging is not implemented yet')
        except ObjectTypeMismatchError as err:
            raise restless.exceptions.Conflict(
                'object type {}'.format(str(err)))
        except ExternalIDMismatchError as err:
            raise restless.exceptions.Conflict(str(err))

        # FIXME: this is ugly
        def map_attributes(type, attrs):
            if not isinstance(attrs, list):
                attrs = [attrs]
            return [{'type': type, **attr} for attr in attrs]

        try:
            attributes = itertools.chain.from_iterable(
                [map_attributes(t, a)
                 for t, a in data['attributes'].items()])
        except KeyError:
            raise restless.exceptions.BadRequest('Missing key `attributes`')

        try:
            obj.add_attributes(attributes, scrap.platform)
        except KeyError:
            raise restless.exceptions.BadRequest('Malformed attribute')

        # We need to save the object first to reload the links
        db.session.add(obj)
        db.session.commit()

        # Find the link created for this platform and add the scrap to it
        link = next((link for link in obj.links
                     if link.platform == scrap.platform), None)
        if link is not None:
            link.scraps.append(scrap)
        else:
            # FIXME: proper error handling
            print('could not find link in {}'.format(obj.links))

        db.session.commit()

        return obj
