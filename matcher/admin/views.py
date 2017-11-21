from operator import eq
from functools import partial
from flask import url_for
from flask_admin.contrib.sqla import ModelView
from flask_admin.form import rules
from flask_admin.model.template import macro, EndpointLinkRowAction
from jinja2 import escape

from ..app import db
from ..scheme.object import ObjectLink, ExternalObject, ExternalObjectType
from ..scheme.platform import Platform, PlatformType
from ..scheme.value import Value, ValueType
from .utils import CustomAdminConverter
from .filters import ExternalObjectPlatformFilter, ExternalObjectSimilarFilter


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


def attribute_formatter(f=lambda _: True, show_score=False,
                        filter=lambda _: True):
    def formatter(view, context, model, name):
        m = context.resolve('attributes_link')
        attrs = [attr for attr in model.attributes
                 if f(attr.type) and filter(attr.text)]
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
    pass


class PlatformView(DefaultView):
    can_view_details = True
    can_export = True
    column_list = ('id', 'type', 'group', 'name', 'slug', 'country', 'links')
    column_searchable_list = ['name', 'slug', 'country']
    column_filters = ['type', 'country', 'group']
    column_editable_list = ['country', 'name', 'slug', 'group']
    form_columns = ('type', 'group', 'name', 'slug', 'url', 'country',
                    'max_rating', 'base_score')
    column_formatters = {
        'links': count_formatter
    }

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
            rules.Field('max_rating'),
            rules.Field('base_score'),
        ], header="Technical info")
    ]


class ScrapView(DefaultView):
    can_view_details = True
    form_columns = ('platform', 'date', 'status', 'stats')
    column_list = ('platform', 'date', 'status')
    column_details_list = ('id', 'platform', 'date', 'status', 'stats')


class ValueView(DefaultView):
    column_list = ('id', 'external_object', 'type', 'text', 'score')
    column_details_list = ('id', 'external_object', 'type', 'text', 'score',
                           'sources')
    column_filters = ['type', 'score', 'external_object']
    column_searchable_list = ['text']
    can_view_details = True
    can_edit = False
    column_formatters = {
        'external_object': link_formatter('allobject.details_view'),
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
        'external_object': link_formatter('allobject.details_view'),
        'platform': link_formatter('platform.edit_view')
    }
    column_searchable_list = ['external_id']


class ExternalObjectView(DefaultView):
    def __init__(self, *args, **kwargs):
        kwargs['category'] = 'External Objects'
        kwargs['endpoint'] = kwargs['name'].lower() + 'object'
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
        'date': attribute_formatter(partial(eq, ValueType.DATE)),
        'genres': attribute_formatter(partial(eq, ValueType.GENRES)),
        'country': attribute_formatter(partial(eq, ValueType.COUNTRY),
                                       filter=lambda t: len(t) == 2),
        'duration': attribute_formatter(partial(eq, ValueType.DURATION),
                                        filter=lambda t: t.replace('.', '')
                                                          .isdigit()),
        'year': attribute_formatter(partial(eq, ValueType.DATE),
                                    filter=lambda t: len(t) == 4),
        'attributes': attribute_formatter(show_score=True),
        'attributes_list': macro('attributes_list'),
        'links_list': macro('links_list'),
        'links': count_formatter
    }

    column_extra_row_actions = [
        EndpointLinkRowAction('glyphicon icon-search',
                              'allobject.index_view', id_arg='flt0_0')
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
    ]

    def get_query(self):
        q = super(ExternalObjectView, self).get_query()
        if hasattr(self, 'external_object_type'):
            q = q.filter(ExternalObject.type == self.external_object_type)
        return q

    def get_count_query(self):
        q = super(ExternalObjectView, self).get_count_query()
        if hasattr(self, 'external_object_type'):
            q = q.filter(ExternalObject.type == self.external_object_type)
        return q


class AllObjectView(ExternalObjectView):
    column_list = ('id', 'type', 'attributes', 'links')
    column_filters = ExternalObjectView.column_filters + ['type']


class PersonObjectView(ExternalObjectView):
    external_object_type = ExternalObjectType.PERSON
    column_list = ('id', 'name', 'links')


class MovieObjectView(ExternalObjectView):
    external_object_type = ExternalObjectType.MOVIE
    column_list = ('id', 'title', 'date', 'genres', 'duration', 'country',
                   'links')
