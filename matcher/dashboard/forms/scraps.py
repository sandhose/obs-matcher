from wtforms import Form, SelectMultipleField
from wtforms_alchemy import QuerySelectMultipleField

from matcher.filters import badge_display
from matcher.scheme.enums import ScrapStatus


class ScrapListFilter(Form):
    platforms = QuerySelectMultipleField(
        "Platforms",
        get_pk=lambda p: p.slug,
        render_kw={"class": "select2 form-control"},
    )
    status = SelectMultipleField(
        "Status",
        choices=[(e.name, badge_display(e)) for e in ScrapStatus],
        render_kw={"class": "select2 form-control"},
    )
    sessions = QuerySelectMultipleField(
        "Session", render_kw={"class": "select2 form-control"}
    )


class EditScrapForm(Form):
    sessions = QuerySelectMultipleField(
        "Sessions", render_kw={"class": "select2 form-control"}
    )
