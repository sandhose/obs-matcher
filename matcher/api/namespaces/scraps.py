from flask_restplus import Namespace, reqparse
from matcher.scheme.platform import Scrap, ScrapStatus, Platform

from .. import models, pagination, inputs
from ..resources import DbResource

api = Namespace('scraps', description='Scrap operations')

scrap_arguments = reqparse.RequestParser()
scrap_arguments.add_argument('platform', required=True)
scrap_arguments.add_argument('status', required=False, type=inputs.custom_enum(ScrapStatus))

edit_scrap_arguments = reqparse.RequestParser()
edit_scrap_arguments.add_argument('stats', required=False, type=dict)
edit_scrap_arguments.add_argument('status', required=False, type=inputs.custom_enum(ScrapStatus))

for key in ['platform', 'scrap']:
    model = getattr(models, key)
    api.models[model.name] = model


@api.route('/')
class ScrapList(DbResource):
    """List and create scraps"""

    @api.doc('list_scraps')
    @pagination.wrap(api, models.scrap)
    def get(self):
        """List all scraps"""
        return self.query(Scrap)

    @api.doc('create_scrap')
    @api.expect(scrap_arguments)
    @api.marshal_with(models.scrap)
    def post(self):
        """
        Create a new scrap

        :raise matcher.exceptions.InvalidStatusTransition:
        """
        args = scrap_arguments.parse_args()

        platform = Platform.lookup(self.session, args['platform'])

        if platform is None:
            raise Exception('Platform not found')

        scrap = Scrap(platform=platform, status=ScrapStatus.SCHEDULED)

        if args['status']:
            scrap.to_status(args['status'])

        self.session.add(scrap)
        self.session.commit()

        return scrap


@api.route('/<int:id>')
@api.response(404, 'Scrap not found')
class ScrapItem(DbResource):
    """Show a single scrap and lets you edit and delete them"""

    def dispatch_request(self, id, *args, **kwargs):
        # Fetch the scrap and raise 404 if it does not exists
        scrap = self.query(Scrap).get_or_404(id)

        return super().dispatch_request(scrap, *args, **kwargs)

    @api.doc('get_scrap')
    @api.marshal_with(models.scrap)
    def get(self, scrap):
        """Fetch a single scrap"""
        return scrap

    @api.doc('put_scrap')
    @api.expect(edit_scrap_arguments)
    @api.marshal_with(models.scrap)
    def put(self, scrap):
        """Edit a scrap"""
        args = edit_scrap_arguments.parse_args()

        if args['stats']:
            scrap.status = args['status']

        if args['status']:
            scrap.to_status(args['status'])

        self.session.commit()

        return scrap
