from flask import url_for
from flask_admin.contrib.sqla import ModelView
from flask_admin.form import rules
from flask_admin.model.template import macro
from jinja2 import escape

from ..scheme.object import ObjectLink
from ..scheme.platform import Platform
from ..scheme.value import Value, ValueType
from .utils import CustomAdminConverter
from .filters import ExternalObjectPlatformFilter


class DefaultView(ModelView):
    model_form_converter = CustomAdminConverter


class PlatformGroupView(DefaultView):
    pass


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


def attribute_formatter(type):
    def formatter(view, context, model, name):
        return next((attr.text for attr in model.attributes
                     if attr.type == type), None)
    return formatter


class PlatformView(DefaultView):
    can_view_details = True
    column_list = ('id', 'group', 'name', 'slug', 'url', 'country')
    column_searchable_list = ['name', 'slug', 'country']
    column_filters = ['country', 'group']
    column_editable_list = ['country', 'name', 'slug', 'group', 'url']
    form_columns = ('group', 'name', 'slug', 'url', 'country', 'max_rating',
                    'base_score')

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
    form_columns = ('platform', 'date', 'status')


class ValueView(DefaultView):
    column_list = ('id', 'external_object', 'type', 'text', 'score')
    column_filters = ['type', 'score', 'external_object']
    column_searchable_list = ['text']


class ObjectLinkView(DefaultView):
    column_formatters = {
        'external_object': link_formatter('externalobject.details_view'),
        'platform': link_formatter('platform.edit_view')
    }


class ExternalObjectView(DefaultView):
    can_view_details = True

    # TODO: Do awesome attribute view
    column_details_list = ('id', 'type', 'attributes', 'links')
    column_list = ('id', 'type', 'title', 'date', 'genres', 'duration')
    column_formatters = {
        'title': attribute_formatter(ValueType.TITLE),
        'date': attribute_formatter(ValueType.DATE),
        'genres': attribute_formatter(ValueType.GENRES),
        'duration': attribute_formatter(ValueType.DURATION),
        'attributes': macro('attributes_list'),
        'links': macro('links_list')
    }
    inline_models = (
        (Value, dict(form_columns=('id', 'type', 'text'))),
        (ObjectLink, dict(form_columns=('id', 'platform', 'external_id'))))
    column_filters = [
        'type',
        ExternalObjectPlatformFilter(
            column=Platform.country,
            name='Country',
            options=[(c, str(c).upper())
                     for c in set((p.country for p in Platform.query.all()))]
        ),
        ExternalObjectPlatformFilter(
            column=Platform.slug,
            name='Platform',
            options=[(p.slug, p.name) for p in Platform.query.all()]
        )
    ]
