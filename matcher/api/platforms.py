from flask import Request

from flask_restplus import Mask, Namespace, abort, fields, inputs, reqparse
from injector import inject
from matcher.scheme.platform import Platform, PlatformGroup, PlatformType

from . import pagination
from .resources import DbResource

api = Namespace('platforms', description='Platform operations')

platform_base =  api.model('Platform', {
    'id': fields.Integer,
    'type': fields.String(enum=['tvod', 'svod', 'global', 'info']),
    'slug': fields.String,
    'name': fields.String,
    'country': fields.String,
    'base_score': fields.Integer,
    'group_id': fields.Integer,
})

platform_group = api.model('Platform Group', {
    'id': fields.Integer,
    'name': fields.String,
    'platforms': fields.List(fields.Nested(platform_base))
}, mask='id,name,platforms{id,type,slug,name,country}')

platform = platform_base.clone('Platform', {
    'group': fields.Nested(platform_group, allow_null=True),
})

# It works, alright?
platform.__mask__ = Mask('id,type,slug,name,country,group{id,name}')

platform_arguments = reqparse.RequestParser()
platform_arguments.add_argument('type', type=str, choices=['tvod', 'svod', 'global', 'info'], required=False)
platform_arguments.add_argument('name', type=str, required=False)
platform_arguments.add_argument('slug', type=str, required=False)
platform_arguments.add_argument('country', type=inputs.regex('^[A-Z]{2}$'), required=False)
platform_arguments.add_argument('base_score', type=int, required=False)
platform_arguments.add_argument('group_id', type=int, required=False)

platform_group_arguments = reqparse.RequestParser()
platform_group_arguments.add_argument('name', type=str, required=False)

@api.route('/')
class PlatformList(DbResource):
    """List all platforms"""

    @api.doc('list_platforms')
    @pagination.wrap(api, platform)
    def get(self):
        """List all platforms"""
        return self.query(Platform)

    @api.doc('create_platform')
    @api.expect(platform_arguments)
    @api.marshal_with(platform)
    def post(self):
        """Create a new platform"""
        args = platform_arguments.parse_args()

        args['type'] = PlatformType.from_name(args['type'])

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
    @api.marshal_with(platform)
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
    @api.marshal_with(platform)
    def put(self, platform):
        """Edit a platform"""
        args = platform_arguments.parse_args()

        args['type'] = PlatformType.from_name(args['type'])

        for key in args:
            if args[key] is not None:
                setattr(platform, key, args[key])

        self.session.commit()

        return platform

@api.route('/groups/')
class PlatformGroupList(DbResource):
    """List and create platform groups"""

    @api.doc('list_platform_groups')
    @pagination.wrap(api, platform_group)
    def get(self):
        """List all platform groups"""
        return self.query(PlatformGroup)

    @api.doc('create_platform_group')
    @api.expect(platform_group_arguments)
    @api.marshal_with(platform_group)
    def post(self):
        """Create a new platform group"""
        args = platform_group_arguments.parse_args()

        platform_group = PlatformGroup(**args)
        self.session.add(platform_group)
        self.session.commit()

        return platform_group

@api.route('/groups/<int:id>')
@api.response(404, 'Platform group not found')
class PlatformGroupItem(DbResource):
    """Show a single platform group and lets you edit and delete them"""

    def dispatch_request(self, id, *args, **kwargs):
        # Fetch the platform and raise 404 if it does not exists
        platform_group = self.query(PlatformGroup).get_or_404(id)

        return super().dispatch_request(platform_group, *args, **kwargs)

    @api.doc('get_platform_group')
    @api.marshal_with(platform_group)
    def get(self, platform_group):
        """Fetch a single group"""
        return platform_group

    @api.doc('delete_platform_group')
    def delete(self, platform_group):
        """Delete a group"""
        self.session.delete(platform_group)
        self.session.commit()

        return 'ok'

    @api.doc('put_platform_group')
    @api.expect(platform_group_arguments)
    @api.marshal_with(platform_group)
    def put(self, platform_group):
        """Edit a group"""
        args = platform_group_arguments.parse_args()

        for key in args:
            if args[key] is not None:
                setattr(platform_group, key, args[key])

        self.session.commit()

        return platform_group
