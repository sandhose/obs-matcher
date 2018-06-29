from wtforms import Form, SelectMultipleField, StringField
from wtforms.ext.sqlalchemy.fields import QuerySelectMultipleField

from matcher.scheme.platform import PlatformType


class PlatformListFilter(Form):
    search = StringField("Search")
    type = SelectMultipleField("Type", choices=[(v.name, v.name) for v in PlatformType])
    country = QuerySelectMultipleField("Country", get_pk=lambda o: o[0], get_label=lambda o: o[0])
