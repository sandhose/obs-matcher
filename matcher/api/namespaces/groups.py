from flask_restplus import Namespace, reqparse

from matcher.scheme.platform import PlatformGroup

from .. import models, pagination
from ..resources import DbResource

api = Namespace("groups", description="Platform group operations")

platform_group_arguments = reqparse.RequestParser()
platform_group_arguments.add_argument("name", type=str, required=False)

for key in ["platform_base", "platform", "platform_group"]:
    model = getattr(models, key)
    api.models[model.name] = model


@api.route("/")
class PlatformGroupList(DbResource):
    """List and create platform groups"""

    @api.doc("list_platform_groups")
    @pagination.wrap(api, models.platform_group)
    def get(self):
        """List all platform groups"""
        return self.query(PlatformGroup)

    @api.doc("create_platform_group")
    @api.expect(platform_group_arguments)
    @api.marshal_with(models.platform_group)
    def post(self):
        """Create a new platform group"""
        args = platform_group_arguments.parse_args()

        platform_group = PlatformGroup(**args)
        self.session.add(platform_group)
        self.session.commit()

        return platform_group


@api.route("/<int:id>")
@api.response(404, "Platform group not found")
class PlatformGroupItem(DbResource):
    """Show a single platform group and lets you edit and delete them"""

    def dispatch_request(self, id, *args, **kwargs):
        # Fetch the platform and raise 404 if it does not exists
        platform_group = self.query(PlatformGroup).get_or_404(id)

        return super().dispatch_request(platform_group, *args, **kwargs)

    @api.doc("get_platform_group")
    @api.marshal_with(models.platform_group)
    def get(self, platform_group):
        """Fetch a single group"""
        return platform_group

    @api.doc("delete_platform_group")
    def delete(self, platform_group):
        """Delete a group"""
        self.session.delete(platform_group)
        self.session.commit()

        return "ok"

    @api.doc("put_platform_group")
    @api.expect(platform_group_arguments)
    @api.marshal_with(models.platform_group)
    def put(self, platform_group):
        """Edit a group"""
        args = platform_group_arguments.parse_args()

        for key in args:
            if args[key] is not None:
                setattr(platform_group, key, args[key])

        self.session.commit()

        return platform_group
