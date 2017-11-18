from flask import url_for
from flask_admin.contrib.sqla import ModelView
from flask_admin.form import rules
from flask_admin.model.template import macro, EndpointLinkRowAction
from jinja2 import escape
from sqlalchemy.sql import alias

from ..scheme.object import ObjectLink
from ..scheme.platform import Platform
from ..scheme.value import Value, ValueType
from .utils import CustomAdminConverter
from .filters import ExternalObjectPlatformFilter, ExternalObjectSimilarFilter


class DefaultView(ModelView):
    model_form_converter = CustomAdminConverter


class PlatformGroupView(DefaultView):
    pass


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


def attribute_formatter(*args):
    def formatter(view, context, model, name):
        attrs = [attr.text for attr in model.attributes
                 if attr.type in args]
        return " || ".join(attrs[:3])
    return formatter


def count_formatter(view, context, model, name):
    return len(getattr(model, name))


class PlatformView(DefaultView):
    can_view_details = True
    column_list = ('id', 'group', 'name', 'slug', 'country', 'links')
    column_searchable_list = ['name', 'slug', 'country']
    column_filters = ['country', 'group']
    column_editable_list = ['country', 'name', 'slug', 'group']
    form_columns = ('group', 'name', 'slug', 'url', 'country', 'max_rating',
                    'base_score')
    column_formatters = {
        'links': count_formatter
    }

    form_rules = [
        rules.FieldSet([
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
        'external_object': link_formatter('externalobject.details_view'),
        'sources': links_formatter('valuesource.details_view'),
    }


class ObjectLinkView(DefaultView):
    column_formatters = {
        'external_object': link_formatter('externalobject.details_view'),
        'platform': link_formatter('platform.edit_view')
    }
    column_searchable_list = ['external_id']


class ExternalObjectView(DefaultView):
    can_view_details = True
    can_export = True
    export_types = ['csv', 'xls']

    # TODO: Do awesome attribute view
    column_details_list = ('id', 'type', 'attributes', 'links_list')
    column_list = ('id', 'type', 'title', 'date', 'genres', 'duration', 'links')
    column_formatters = {
        'title': attribute_formatter(ValueType.TITLE, ValueType.NAME),
        'date': attribute_formatter(ValueType.DATE),
        'genres': attribute_formatter(ValueType.GENRES),
        'duration': attribute_formatter(ValueType.DURATION),
        'attributes': macro('attributes_list'),
        'links_list': macro('links_list'),
        'links': count_formatter
    }

    column_extra_row_actions = [
        EndpointLinkRowAction('glyphicon icon-search',
                              'externalobject.index_view', id_arg='flt0_0')
    ]

    inline_models = (
        (Value, dict(form_columns=('id', 'type', 'text'))),
        (ObjectLink, dict(form_columns=('id', 'platform', 'external_id'))))

    column_filters = [
        ExternalObjectSimilarFilter(name='Similar'),
        'type',
        ExternalObjectPlatformFilter(
            column=Platform.country,
            name='Country',
            options=lambda: [
                (c, str(c).upper())
                for c in set((p.country for p in Platform.query.all()))
            ]
        ),
        ExternalObjectPlatformFilter(
            column=Platform.slug,
            name='Platform',
            options=lambda: [
                (p.slug, p.name)
                for p in Platform.query.all()
            ]
        ),
    ]
