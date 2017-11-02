from flask_admin.contrib.sqla import ModelView
from flask_admin.form import rules

from ..scheme.object import ObjectLink
from ..scheme.platform import Platform
from ..scheme.value import Value
from .utils import CustomAdminConverter
from .filters import ExternalObjectPlatformFilter


class DefaultView(ModelView):
    model_form_converter = CustomAdminConverter


class PlatformGroupView(DefaultView):
    inline_models = (Platform,)


class PlatformView(DefaultView):
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


class ValueView(DefaultView):
    column_list = ('id', 'external_object', 'type', 'text', 'score')
    column_filters = ['type', 'score', 'external_object']
    column_searchable_list = ['text']


class ExternalObjectView(DefaultView):
    column_list = ('id', 'type', 'attributes')
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
