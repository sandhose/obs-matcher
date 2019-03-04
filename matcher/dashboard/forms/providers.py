from wtforms import Form, FormField, HiddenField, StringField, SubmitField, validators
from wtforms_alchemy import ModelFieldList, ModelForm, QuerySelectField

from matcher.scheme.provider import Provider, ProviderPlatform


class ProviderListFilter(Form):
    search = StringField("Search")


class ProviderPlatformForm(ModelForm):
    class Meta:
        model = ProviderPlatform
        only = ["public", "home_url"]

    provider_id = HiddenField()
    platform_id = HiddenField()
    delete = SubmitField(
        "Delete", render_kw={"class": "btn btn-danger btn-sm btn-block"}
    )

    def process(self, formdata=None, obj=None, data=None, **kwargs):
        if obj:
            self.platform_obj = obj.platform
        elif data:
            self.platform_obj = data["platform"]
        return super(ProviderPlatformForm, self).process(
            formdata=formdata, obj=obj, data=data, **kwargs
        )


class NewProviderForm(ModelForm):
    class Meta:
        model = Provider


class EditProviderForm(ModelForm):
    class Meta:
        model = Provider

    provider_platforms = ModelFieldList(FormField(ProviderPlatformForm))

    platform_to_add = QuerySelectField(
        "Platform",
        get_label=lambda p: p.name,
        validators=[validators.Optional()],
        render_kw={"class": "form-control select2"},
        allow_blank=True,
    )
    add_platform = SubmitField(
        "Add", render_kw={"class": "btn btn-success btn-sm btn-block"}
    )
