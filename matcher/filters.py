import pendulum
from flask import Flask, request
from jinja2 import Markup, escape

from matcher.scheme.enums import (ExportFactoryIterator, ExportFileStatus,
                                  ExportRowType, ExternalObjectType,
                                  PlatformType, ScrapStatus,)
from matcher.scheme.utils import CustomEnum


def relative_date(dt):
    """Intelligently show a human-readable date inside an <abbr>

    It shows a relative date if was less than 3 days ago, otherwise it shows
    the full one. The other date (relative when showing the absolute one and
    vice-versa) is always shown inside an <abbr>.
    """
    dt = pendulum.instance(dt)
    human = escape(dt.diff_for_humans())
    full = escape(dt.to_datetime_string())
    fmt = {'title': full, 'display': human} if dt.diff().days < 3 else {'title': human, 'display': full}
    return Markup(
        '<abbr title="{title}">{display}</abbr>'.format(**fmt)
    )


def query():
    """Inject the query args without the page and per_page parameters"""
    query = request.args.copy()
    query.pop('page', '')
    query.pop('per_page', '')
    return dict(query=query)


def badge_color(type_: CustomEnum) -> str:
    return {
        ExternalObjectType.MOVIE: 'primary',
        ExternalObjectType.SERIES: 'success',
        ExternalObjectType.EPISODE: 'info',
        ExternalObjectType.PERSON: 'secondary',

        PlatformType.GLOBAL: 'secondary',
        PlatformType.INFO: 'info',
        PlatformType.SVOD: 'danger',
        PlatformType.TVOD: 'primary',

        ScrapStatus.SCHEDULED: 'secondary',
        ScrapStatus.RUNNING: 'primary',
        ScrapStatus.SUCCESS: 'success',
        ScrapStatus.ABORTED: 'warning',
        ScrapStatus.FAILED: 'danger',

        ExportFileStatus.SCHEDULED: 'secondary',
        ExportFileStatus.QUERYING: 'info',
        ExportFileStatus.PROCESSING: 'primary',
        ExportFileStatus.DONE: 'success',
        ExportFileStatus.FAILED: 'danger',
        ExportFileStatus.ABSENT: 'danger',

        ExportRowType.EXTERNAL_OBJECT: 'primary',
        ExportRowType.OBJECT_LINK: 'info',

        ExportFactoryIterator.PLATFORMS: 'info',
        ExportFactoryIterator.GROUPS: 'success',
        ExportFactoryIterator.COUNTRIES: 'primary',
    }.get(type_, 'secondary')


def transition_color(method):
    if hasattr(method, 'transition'):
        return badge_color(method.transition.to_state)
    else:
        return 'secondary'


def template_highlight(template: str):
    template = escape(template)
    return template.\
        replace('{{', Markup('<span class="badge badge-secondary badge-pill">')).\
        replace('}}', Markup('</span>'))


def filename(path: str) -> str:
    return path.split('/')[-1]


def register(app: Flask):
    """Register the filters and context processors for jinja"""
    app.jinja_env.filters['relative_date'] = relative_date
    app.jinja_env.filters['badge_color'] = badge_color
    app.jinja_env.filters['transition_color'] = transition_color
    app.jinja_env.filters['template_highlight'] = template_highlight
    app.jinja_env.filters['filename'] = filename
    app.context_processor(query)
