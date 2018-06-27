import pendulum
from jinja2 import Markup, escape


def relative_date(dt):
    dt = pendulum.instance(dt)
    display = dt.diff_for_humans() if dt.diff().days < 3 else dt.to_datetime_string()
    return Markup(
        '<abbr title="{}">{}</abbr>'
        .format(escape(dt.to_datetime_string()), escape(display))
    )


def register(app):
    app.jinja_env.filters['relative_date'] = relative_date
