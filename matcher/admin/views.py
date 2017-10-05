from flask_admin.contrib.sqla import ModelView

from ..scheme.value import Value
from ..scheme.object import ObjectLink
from ..scheme.platform import Platform
from .utils import CustomAdminConverter


class DefaultView(ModelView):
    model_form_converter = CustomAdminConverter


class PlatformGroupView(DefaultView):
    inline_models = (Platform,)


class ExternalObjectView(DefaultView):
    column_list = ('id', 'type', 'attributes')
    inline_models = (Value, ObjectLink,)
