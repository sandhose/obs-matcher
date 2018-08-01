from wtforms import (Form, FormField, IntegerField, SelectMultipleField,
                     StringField,)
from wtforms.ext.sqlalchemy.fields import QuerySelectMultipleField, QuerySelectField

from matcher.filters import badge_display
from matcher.scheme.enums import ExternalObjectType


class ExternalIDForm(Form):
    platform = QuerySelectField("Platform", render_kw={'class': 'select2 form-control'})
    external_id = StringField("External ID")


class ObjectListFilter(Form):
    search = StringField("Search")
    country = StringField("Country")
    type = SelectMultipleField("Type", choices=[(v.name, badge_display(v)) for v in ExternalObjectType],
                               render_kw={'class': 'select2 form-control'})
    platform = QuerySelectMultipleField("Platform", render_kw={'class': 'select2 form-control'})
    session = QuerySelectMultipleField("Session", render_kw={'class': 'select2 form-control'})
    scrap = IntegerField("Scrap")
    object_link = FormField(ExternalIDForm)
