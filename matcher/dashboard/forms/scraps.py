from wtforms import Form, SelectMultipleField

from matcher.filters import badge_display
from matcher.scheme.enums import ScrapStatus

from .fields import SelectAJAXMultipleField


class ScrapListFilter(Form):
    platforms = SelectAJAXMultipleField('Platforms')
    status = SelectMultipleField('Status', choices=[(e.name, badge_display(e)) for e in ScrapStatus])
