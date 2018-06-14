from injector import inject
from flask import Request
from flask_restplus import Namespace, fields, abort, reqparse, inputs

from matcher.scheme.platform import Platform
from .resources import DbResource
from . import pagination

api = Namespace('platforms', description='Platform operations')

platform_group = api.model('Platform Group', {
    'id': fields.Integer,
    'name': fields.String,
})

platform = api.model('Platform', {
    'id': fields.Integer,
    'slug': fields.String,
    'name': fields.String,
    'country': fields.String,
    'base_score': fields.Integer,
    'group': fields.Nested(platform_group, allow_null=True),
    'group_id': fields.Integer,
}, mask='id,slug,name,country,group{id,name}')

platform_group['platforms'] = fields.List(fields.Nested(platform))

@api.route('/')
class PlatformList(DbResource):
    """List all platforms"""

    @api.doc('list_platforms')
    @pagination.wrap(api, platform)
    def get(self):
        """List all platforms"""
        return self.query(Platform)


@api.route('/<int:id>')
@api.response(404, 'Platform not found')
class PlatformItem(DbResource):
    """Show a single platform and lets you edit and delete them"""

    arguments = reqparse.RequestParser()
    arguments.add_argument('name', type=str, required=False)
    arguments.add_argument('slug', type=str, required=False)
    arguments.add_argument('country', type=inputs.regex('^[A-Z]{2}$'), required=False)
    arguments.add_argument('base_score', type=int, required=False)
    arguments.add_argument('group_id', type=int, required=False)

    @api.doc('get_platform')
    @api.marshal_with(platform)
    def get(self, id):
        """Fetch a single platform"""
        platform = self.query(Platform).get(id)

        if platform is None:
            abort(404, 'Platform not found')

        return platform

    @api.doc('delete_platform')
    def delete(self, id):
        """Delete a platform"""
        platform = self.query(Platform).get(id)

        if platform is None:
            abort(404, 'Platform not found')

        self.session.delete(platform)
        self.session.commit()

        return 'ok'

    @api.doc('put_platform')
    @api.expect(arguments)
    @api.marshal_with(platform)
    def put(self, id):
        """Edit a platform"""

        platform = self.query(Platform).get(id)

        if platform is None:
            abort(404, 'Platform not found')

        args = self.arguments.parse_args()

        for key in args:
            if args[key] is not None:
                setattr(platform, key, args[key])

        self.session.commit()

        return platform
