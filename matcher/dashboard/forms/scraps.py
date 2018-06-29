from wtforms import Form, SelectMultipleField

from matcher.scheme.platform import ScrapStatus

from .fields import SelectAJAXMultipleField


class ScrapListFilter(Form):
    platforms = SelectAJAXMultipleField('Platforms')
    status = SelectMultipleField('Status', choices=[(e.name, e.name) for e in ScrapStatus])
