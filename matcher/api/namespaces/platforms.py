from flask_restplus import Namespace, inputs, reqparse

from matcher.scheme.enums import PlatformType
from matcher.scheme.platform import Platform

from .. import models, pagination
from ..inputs import custom_enum
from ..resources import DbResource

api = Namespace('platforms', description='Platform operations')

platform_arguments = reqparse.RequestParser()
platform_arguments.add_argument('type', type=custom_enum(PlatformType), required=False)
platform_arguments.add_argument('name', type=str, required=False)
platform_arguments.add_argument('slug', type=str, required=False)
platform_arguments.add_argument('country', type=inputs.regex('^[A-Z]{2}$'), required=False)
platform_arguments.add_argument('base_score', type=int, required=False)
platform_arguments.add_argument('group_id', type=int, required=False)

search_arguments = reqparse.RequestParser()
search_arguments.add_argument('q', type=str, required=False)

for key in ['platform_base', 'platform', 'platform_group']:
    model = getattr(models, key)
    api.models[model.name] = model


@api.route('/')
class PlatformList(DbResource):
    """List all platforms"""

    @api.doc('list_platforms')
    @pagination.wrap(api, models.platform, arguments=[search_arguments])
    def get(self):
        """List all platforms"""
        query = self.query(Platform)

        search_args = search_arguments.parse_args()
        if search_args['q']:
            query = query.filter(Platform.search_filter(search_args['q']))

        return query

    @api.doc('create_platform')
    @api.expect(platform_arguments)
    @api.marshal_with(models.platform)
    def post(self):
        """Create a new platform

        :raises IntegrityError: Raised when the slug is not unique
        """
        args = platform_arguments.parse_args()

        platform = Platform(**args)
        self.session.add(platform)
        self.session.commit()

        return platform


@api.route('/<int:id>')
@api.response(404, 'Platform not found')
class PlatformItem(DbResource):
    """Show a single platform and lets you edit and delete them"""

    def dispatch_request(self, id, *args, **kwargs):
        # Fetch the platform and raise 404 if it does not exists
        platform = self.query(Platform).get_or_404(id)

        return super().dispatch_request(platform, *args, **kwargs)

    @api.doc('get_platform')
    @api.marshal_with(models.platform)
    def get(self, platform):
        """Fetch a single platform"""
        return platform

    @api.doc('delete_platform')
    def delete(self, platform):
        """Delete a platform"""
        self.session.delete(platform)
        self.session.commit()

        return 'ok'

    @api.doc('put_platform')
    @api.expect(platform_arguments)
    @api.marshal_with(models.platform)
    def put(self, platform):
        """Edit a platform

        :raises IntegrityError: Raised when the slug is not unique
        """
        args = platform_arguments.parse_args()

        for key in args:
            if args[key] is not None:
                setattr(platform, key, args[key])

        self.session.commit()

        return platform
