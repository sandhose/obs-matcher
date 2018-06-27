from functools import partial
from operator import eq

from flask import url_for
from flask_admin.contrib.sqla import ModelView
from flask_admin.form import rules
from flask_admin.model.template import EndpointLinkRowAction, macro
from jinja2 import escape
from sqlalchemy.orm import joinedload

from ..app import db
from ..scheme.object import (Episode, ExternalObject, ExternalObjectType,
                             ObjectLink,)
from ..scheme.platform import Platform, PlatformType
from ..scheme.value import Value, ValueType
from .filters import (ExternalObjectPlatformFilter,
                      ExternalObjectSimilarFilter, SeriesFilter,)
from .utils import CustomAdminConverter


def links_formatter(route):
    def formatter(view, context, model, name):
        list = ''.join([
            '<li><a href="{}">{}</a></li>'
            .format(
                url_for(route),
                escape(item)
            )
            for item in getattr(model, name)
        ])
        return rules.Markup(
            '<ul>' + list + '</ul>'
        )
    return formatter


def link_formatter(route):
    def formatter(view, context, model, name):
        return rules.Markup(
            '<a href="{}">{}</a>'
            .format(
                url_for(route, id=getattr(model, name).id),
                escape(getattr(model, name))
            )
        )
    return formatter


def series_formatter(view, context, model, name):
    series = model.related_object.series
    if series is not None:
        return rules.Markup(
            '<a href="{}">{}</a>'
            .format(
                url_for('series.details_view', id=series.id),
                escape(repr(series))
            )
        )


def meta_formatter(attr):
    def formatter(view, context, model, name):
        return rules.Markup(str(getattr(model.related_object, attr)))
    return formatter


def episodes_formatter(view, context, model, name):
    count = db.session.query(Episode).filter(Episode.series == model).count()
    return rules.Markup('<a href="{}">{}</a>'.format(
        url_for('episodes.index_view', flt1_5=model.id),
        count)
    )


def attribute_formatter(f=lambda _: True, show_score=False,
                        filter=lambda _: True, limit=None):
    def formatter(view, context, model, name):
        attrs = [attr for attr in model.attributes
                 if f(attr.type) and filter(attr.text)]
        if limit is not None:
            attrs = attrs[:limit]

        if context is None:
            return ','.join((attr.text for attr in attrs))

        m = context.resolve('attributes_link')
        return m(attributes=attrs, show_score=show_score)
    return formatter


def count_formatter(view, context, model, name):
    return len(getattr(model, name))


class DefaultView(ModelView):
    model_form_converter = CustomAdminConverter


class PlatformGroupView(DefaultView):
    column_list = ('id', 'name', 'platforms')
    column_formatters = {
        'platforms': count_formatter
    }


class PlatformView(DefaultView):
    column_default_sort = 'id'
    can_view_details = True
    can_export = True
    column_list = ('id', 'type', 'group', 'name', 'slug', 'country', 'links_count')
    column_searchable_list = ['name', 'slug', 'country']
    column_filters = ['type', 'country', 'group']
    column_editable_list = ['country', 'name', 'slug', 'group']
    form_columns = ('type', 'group', 'name', 'slug', 'url', 'country',
                    'base_score', 'allow_links_overlap', 'ignore_in_exports')

    form_rules = [
        rules.FieldSet([
            rules.Field('type'),
            rules.Field('group'),
            rules.Field('name'),
            rules.Field('country'),
            rules.Field('url'),
        ], header="Basic info"),
        rules.FieldSet([
            rules.Field('slug'),
            rules.Field('base_score'),
            rules.Field('allow_links_overlap'),
            rules.Field('ignore_in_exports'),
        ], header="Technical info")
    ]


class ScrapView(DefaultView):
    can_view_details = True
    form_columns = ('platform', 'date', 'status', 'stats')
    column_list = ('platform', 'date', 'status', 'links_count')
    column_details_list = ('id', 'platform', 'date', 'status', 'stats')


class ValueView(DefaultView):
    column_list = ('id', 'external_object', 'type', 'text', 'score')
    column_details_list = ('id', 'external_object', 'type', 'text', 'score',
                           'sources')
    column_filters = ['type', 'score']  # , 'external_object']
    column_searchable_list = ['text']
    can_view_details = True
    can_edit = False
    column_formatters = {
        'external_object': link_formatter('allobjects.details_view'),
        'sources': links_formatter('valuesource.details_view'),
    }


class ValueSourceView(DefaultView):
    column_list = ('value', 'platform', 'score_factor')
    column_details_list = ('value', 'platform', 'score_factor')
    can_view_details = True
    can_edit = False
    column_formatters = {
        'value': link_formatter('value.details_view'),
        'platform': link_formatter('platform.details_view'),
    }


class ObjectLinkView(DefaultView):
    column_formatters = {
        'external_object': link_formatter('allobjects.details_view'),
        'platform': link_formatter('platform.edit_view')
    }
    column_searchable_list = ['external_id']


class ExternalObjectView(DefaultView):
    def __init__(self, *args, **kwargs):
        kwargs['category'] = 'External Objects'
        kwargs['endpoint'] = kwargs['name'].lower().replace(' ', '')
        super(ExternalObjectView, self).__init__(ExternalObject, *args,
                                                 **kwargs)

    can_view_details = True
    can_export = True
    # TODO: Export formatters
    export_types = ['csv', 'xls']

    column_details_list = ('id', 'type', 'attributes_list', 'links_list')
    column_formatters = {
        'name': attribute_formatter(partial(eq, ValueType.NAME)),
        'title': attribute_formatter(partial(eq, ValueType.TITLE)),
        'date': attribute_formatter(partial(eq, ValueType.DATE),
                                    filter=lambda t: len(t) == 4),
        'genres': attribute_formatter(partial(eq, ValueType.GENRES),
                                      limit=3),
        'country': attribute_formatter(partial(eq, ValueType.COUNTRY),
                                       filter=lambda t: len(t) == 2),
        'duration': attribute_formatter(partial(eq, ValueType.DURATION),
                                        filter=lambda t: t.replace('.', '')
                                                          .isdigit(),
                                        limit=1),
        'series': series_formatter,
        'season': meta_formatter('season'),
        'episode': meta_formatter('episode'),
        'episode_details': macro('episode_details'),
        'episodes': episodes_formatter,
        'episodes_list': macro('episodes_list'),
        'attributes': attribute_formatter(show_score=True),
        'attributes_list': macro('attributes_list'),
        'links_list': macro('links_list'),
        'links': count_formatter
    }

    column_extra_row_actions = [
        EndpointLinkRowAction('glyphicon icon-search',
                              'allobjects.index_view', id_arg='flt0_0')
    ]

    inline_models = (
        (Value, dict(form_columns=('id', 'type', 'text'))),
        (ObjectLink, dict(form_columns=('id', 'platform', 'external_id'))))

    column_filters = [
        ExternalObjectSimilarFilter(name='Similar'),
        ExternalObjectPlatformFilter(
            column=Platform.country,
            name='Platform',
            options=[
                (c[0], str(c[0]).upper())
                for c in db.session.query(Platform.country).distinct()
            ]
        ),
        ExternalObjectPlatformFilter(
            column=Platform.type,
            name='Platform',
            options=[(t.name, t.name) for t in PlatformType]
        ),
        ExternalObjectPlatformFilter(
            column=Platform.slug,
            name='Platform',
            options=[
                (p.slug, p.name)
                for p in db.session.query(Platform.slug, Platform.name)
            ]
        ),
        ExternalObjectPlatformFilter(
            column=Platform.slug,
            invert=True,
            name='Platform',
            options=[
                (p.slug, p.name)
                for p in db.session.query(Platform.slug, Platform.name)
            ]
        ),
    ]

    def get_query(self):
        q = super(ExternalObjectView, self).get_query()\
            .options(joinedload(ExternalObject.attributes).
                     joinedload(Value.sources))
        if hasattr(self, 'external_object_type'):
            q = q.filter(ExternalObject.type == self.external_object_type)
        return q

    def get_count_query(self):
        q = super(ExternalObjectView, self).get_count_query()
        if hasattr(self, 'external_object_type'):
            q = q.filter(ExternalObject.type == self.external_object_type)
        return q


class AllObjectView(ExternalObjectView):
    column_list = ('id', 'type', 'attributes', 'links_count')
    column_filters = ExternalObjectView.column_filters + ['type']


class PersonView(ExternalObjectView):
    external_object_type = ExternalObjectType.PERSON
    column_list = ('id', 'name', 'links_count')


class MovieView(ExternalObjectView):
    external_object_type = ExternalObjectType.MOVIE
    column_list = ('id', 'title', 'date', 'genres', 'duration', 'country',
                   'links_count')


class SeriesView(ExternalObjectView):
    external_object_type = ExternalObjectType.SERIES
    column_details_list = ('id', 'type', 'attributes_list', 'links_list',
                           'episodes_list')
    column_list = ('id', 'title', 'date', 'genres', 'country', 'episodes',
                   'links_count')


class EpisodeView(ExternalObjectView):
    external_object_type = ExternalObjectType.EPISODE
    column_list = ('id', 'title', 'date', 'series', 'season', 'episode',
                   'country', 'links_count')
    column_details_list = ('id', 'type', 'attributes_list', 'links_list',
                           'episode_details')
    column_filters = ExternalObjectView.column_filters + [
        SeriesFilter(name='Episode')
    ]
