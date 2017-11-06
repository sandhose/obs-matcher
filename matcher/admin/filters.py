from flask_admin.model.filters import BaseFilter

from ..scheme.object import ObjectLink, ExternalObject
from ..scheme.platform import Platform


class ExternalObjectPlatformFilter(BaseFilter):
    def __init__(self, column, name, options=None, data_type=None):
        super(ExternalObjectPlatformFilter, self).__init__(name, options,
                                                           data_type)
        self.column = column

    def apply(self, query, value, alias=None):
        return query.\
            join(ObjectLink,
                 ExternalObject.id == ObjectLink.external_object_id).\
            join(Platform, ObjectLink.platform_id == Platform.id).\
            filter(self.column == value)

    def operation(self):
        return 'is'
