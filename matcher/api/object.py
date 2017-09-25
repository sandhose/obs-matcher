import restless.exceptions
from flask import request
from sqlalchemy.orm.exc import NoResultFound
from restless.preparers import CollectionSubPreparer, SubPreparer, \
    FieldsPreparer

from ..app import db
from .utils import AutoPreparer, CustomFlaskResource
from ..scheme.object import ExternalObject, ExternalObjectType
from ..exceptions import AmbiguousLinkError, ObjectTypeMismatchError, \
    ExternalIDMismatchError, UnknownAttribute
from ..scheme.platform import Scrap


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
        return ExternalObject.query.all()

    def detail(self, pk):
        return ExternalObject.query.filter(ExternalObject.id == pk).one()

    def create(self):
        scrap_id = request.headers.get('x-scrap-id', None)
        if scrap_id is None:
            raise restless.exceptions.BadRequest('Missing `x-scrap-id` header')

        try:
            scrap = Scrap.query.filter(Scrap.id == scrap_id).one()
        except NoResultFound:
            raise restless.exceptions.NotFound('Scrap not found')

        data = ExternalObject.normalize_dict(self.data)

        if data['type'] is None:
            raise restless.exceptions.BadRequest('Field "type" is required')

        if data['relation'] is not None:
            raise restless.exceptions.BadRequest(
                'Field "relation" is not allowed on the root object')

        try:
            obj = ExternalObject.lookup_or_create(
                obj_type=data['type'],
                links=data['links'],
                session=db.session,
            )
        except AmbiguousLinkError as err:
            raise restless.exceptions.Unavailable(str(err))
        except ObjectTypeMismatchError as err:
            raise restless.exceptions.Conflict(str(err))
        except ExternalIDMismatchError as err:
            raise restless.exceptions.Conflict(str(err))

        if data['attributes'] is not None:
            for attribute in data['attributes']:
                try:
                    obj.add_attribute(attribute, scrap.platform)
                except KeyError:
                    raise restless.exceptions.BadRequest('Malformed attribute')
                except UnknownAttribute as e:
                    # FIXME: do something with this exception
                    print(e)

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
            raise Exception('could not find link in {!r}'.format(obj.links))

        db.session.commit()

        return obj
