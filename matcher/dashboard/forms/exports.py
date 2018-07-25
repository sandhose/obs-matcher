from wtforms import Form, SelectMultipleField

from matcher.scheme.enums import (ExportFactoryIterator, ExportRowType,
                                  ExternalObjectType,)


class ExportFactoryListFilter(Form):
    row_type = SelectMultipleField("Type", choices=[(v.name, v.name) for v in ExportRowType])
    iterator = SelectMultipleField("Iterator", choices=[(v.name, v.name) for v in ExportFactoryIterator])
    external_object_type = SelectMultipleField("Objects type", choices=[(v.name, v.name) for v in ExternalObjectType])
