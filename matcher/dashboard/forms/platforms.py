from wtforms import Form, SelectMultipleField, StringField
from wtforms_alchemy import QuerySelectMultipleField

from matcher.filters import badge_display
from matcher.scheme.enums import PlatformType


class PlatformListFilter(Form):
    search = StringField("Search")
    type = SelectMultipleField(
        "Type",
        choices=[(v.name, badge_display(v)) for v in PlatformType],
        render_kw={"class": "form-control select2"},
    )
    country = QuerySelectMultipleField(
        "Country",
        get_pk=lambda o: o[0],
        get_label=lambda o: o[0],
        render_kw={"class": "form-control select2"},
    )
    group = QuerySelectMultipleField(
        "Group", get_label=lambda g: g.name, render_kw={"class": "form-control select2"}
    )
    provider = QuerySelectMultipleField(
        "Provider",
        get_label=lambda p: p.name,
        get_pk=lambda p: p.slug,
        render_kw={"class": "form-control select2"},
    )
