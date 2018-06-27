import pendulum
from jinja2 import Markup, escape


def relative_date(dt):
    dt = pendulum.instance(dt)
    human = escape(dt.diff_for_humans())
    full = escape(dt.to_datetime_string())
    fmt = {'title': full, 'display': human} if dt.diff().days < 3 else {'title': human, 'display': full}
    return Markup(
        '<abbr title="{title}">{display}</abbr>'.format(**fmt)
    )


def register(app):
    app.jinja_env.filters['relative_date'] = relative_date
