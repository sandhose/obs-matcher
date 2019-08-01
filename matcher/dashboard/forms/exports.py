from wtforms import Form, FormField, SelectMultipleField, StringField, validators
from wtforms.ext.sqlalchemy.fields import QuerySelectField, QuerySelectMultipleField

from matcher.filters import badge_display
from matcher.scheme.enums import (
    ExportFactoryIterator,
    ExportFileStatus,
    ExportRowType,
    ExternalObjectType,
    PlatformType,
)


class ExportFactoryListFilter(Form):
    row_type = SelectMultipleField(
        "Type", choices=[(v.name, badge_display(v)) for v in ExportRowType]
    )
    iterator = SelectMultipleField(
        "Iterator", choices=[(v.name, badge_display(v)) for v in ExportFactoryIterator]
    )
    external_object_type = SelectMultipleField(
        "Objects type", choices=[(v.name, badge_display(v)) for v in ExternalObjectType]
    )


class ExportFilter(Form):
    platform_id = QuerySelectMultipleField(
        "Platform", get_label="name", render_kw={"class": "select2"}
    )
    platform_group_id = QuerySelectMultipleField(
        "Group", get_label="name", render_kw={"class": "select2"}
    )
    platform_country = SelectMultipleField(
        "Platform country", render_kw={"class": "select2"}
    )
    platform_type = SelectMultipleField(
        "Platform type",
        choices=[(v.name, v.name) for v in PlatformType],
        render_kw={"class": "select2"},
    )

    def render(self):
        filters = {}
        for i in [
            "platform_id",
            "platform_group_id",
            "platform_country",
            "platform_type",
        ]:
            attr = getattr(self, i)
            if attr.data:
                filters[i.replace("_", ".", 1)] = ",".join(
                    item if isinstance(item, str) else str(item.id)
                    for item in attr.data
                )

        return filters


class NewExportFileForm(Form):
    path = StringField("File name", [validators.InputRequired()])
    session = QuerySelectField(
        "Session", get_label="name", render_kw={"class": "form-control select2"}
    )
    filters = FormField(ExportFilter)
    template = QuerySelectField("Template", render_kw={"class": "form-control select2"})


class ExportFileFilter(Form):
    status = SelectMultipleField(
        "Status",
        choices=[(v.name, badge_display(v)) for v in ExportFileStatus],
        render_kw={"class": "form-control select2"},
    )
    session = QuerySelectMultipleField(
        "Session", get_label="name", render_kw={"class": "form-control select2"}
    )
    factory = QuerySelectMultipleField(
        "Factory", get_label="name", render_kw={"class": "form-control select2"}
    )
    template = QuerySelectMultipleField(
        "Template", render_kw={"class": "form-control select2"}
    )
    row_type = SelectMultipleField(
        "Type",
        choices=[(v.name, badge_display(v)) for v in ExportRowType],
        render_kw={"class": "form-control select2"},
    )
    external_object_type = SelectMultipleField(
        "Objects type",
        choices=[(v.name, badge_display(v)) for v in ExternalObjectType],
        render_kw={"class": "form-control select2"},
    )
