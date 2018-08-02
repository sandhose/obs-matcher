from wtforms import Form, SelectMultipleField
from wtforms.ext.sqlalchemy.fields import QuerySelectMultipleField

from matcher.filters import badge_display
from matcher.scheme.enums import ScrapStatus

from .fields import SelectAJAXMultipleField


class ScrapListFilter(Form):
    platforms = SelectAJAXMultipleField('Platforms')
    status = SelectMultipleField('Status', choices=[(e.name, badge_display(e)) for e in ScrapStatus])


class EditScrapForm(Form):
    sessions = QuerySelectMultipleField("Sessions", get_label=lambda s: s.name,
                                        render_kw={'class': 'select2 form-control'})
