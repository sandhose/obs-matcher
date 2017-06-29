from flask_admin.contrib.sqla import ModelView

from ..scheme import Value, ObjectLink, Platform, Role
from .utils import CustomAdminConverter


class DefaultView(ModelView):
    model_form_converter = CustomAdminConverter


class PlatformGroupView(DefaultView):
    inline_models = (Platform,)


class ExternalObjectView(DefaultView):
    column_list = ('id', 'type', 'attributes')
    inline_models = (Value, ObjectLink,)


class PersonView(DefaultView):
    inline_models = (Role,)
