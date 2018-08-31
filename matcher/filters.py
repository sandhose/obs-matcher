from typing import Mapping  # noqa

import pendulum
from flask import Flask, request
from jinja2 import Markup, escape

from matcher.scheme.enums import (ExportFactoryIterator, ExportFileStatus,
                                  ExportRowType, ExternalObjectType,
                                  ImportFileStatus, PlatformType, ScrapStatus,
                                  ValueType,)
from matcher.scheme.utils import CustomEnum


def relative_date(dt):
    """Intelligently show a human-readable date inside an <abbr>

    It shows a relative date if was less than 3 days ago, otherwise it shows
    the full one. The other date (relative when showing the absolute one and
    vice-versa) is always shown inside an <abbr>.
    """
    try:
        dt = pendulum.instance(dt)
    except ValueError:
        return '–'
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

        ImportFileStatus.UPLOADED: 'secondary',
        ImportFileStatus.PROCESSING: 'primary',
        ImportFileStatus.DONE: 'success',
        ImportFileStatus.FAILED: 'danger',

        ValueType.TITLE: 'primary',
        ValueType.NAME: 'primary',
        ValueType.COUNTRY: 'success',
        ValueType.DATE: 'info',
        ValueType.GENRES: 'danger',
        ValueType.DURATION: 'secondary',
    }.get(type_, 'secondary')


def badge_display(type_: CustomEnum) -> str:
    mapping = {
        ExportFileStatus.SCHEDULED: 'Queued',
        ExportFileStatus.QUERYING: 'Starting',
        ExportFileStatus.PROCESSING: 'Running',
        ExportFileStatus.DONE: 'Done',
        ExportFileStatus.FAILED: 'Failed',
        ExportFileStatus.ABSENT: 'Removed',

        ExportRowType.EXTERNAL_OBJECT: 'Unique',
        ExportRowType.OBJECT_LINK: 'Cumulé',
    }  # type: Mapping[CustomEnum, str]

    return mapping.get(type_, str(type_).upper())


def filter_display(filter_, cache):
    """Display export file filters in a human-readable way"""
    key, value = filter_
    cache_ = cache.get(key, {})

    def get_cache(id_str):
        try:
            return str(cache_[int(id_str)])
        except (KeyError, ValueError):
            return id_str

    title, coerce = {
        'platform.id': ('Platform', get_cache),
        'platform.group_id': ('Group', get_cache),
        'platform.type': ('Type', str),
        'platform.country': ('Country', str),
    }.get(key, (key, str))

    values = [coerce(v.strip()) for v in value.upper().split(',')]

    return title + ': ' + ', '.join(values)


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


def pluralize(number, singular='', plural='s'):
    if number == 1:
        return singular
    else:
        return plural


def register(app: Flask):
    """Register the filters and context processors for jinja"""
    app.jinja_env.filters['relative_date'] = relative_date
    app.jinja_env.filters['badge_color'] = badge_color
    app.jinja_env.filters['badge_display'] = badge_display
    app.jinja_env.filters['filter_display'] = filter_display
    app.jinja_env.filters['transition_color'] = transition_color
    app.jinja_env.filters['template_highlight'] = template_highlight
    app.jinja_env.filters['filename'] = filename
    app.jinja_env.filters['pluralize'] = pluralize
    app.context_processor(query)
