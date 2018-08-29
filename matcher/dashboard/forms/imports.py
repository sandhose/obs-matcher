from flask_wtf import FlaskForm
from flask_wtf.file import FileField, FileRequired
from wtforms import (FieldList, Form, FormField, SelectField, StringField,
                     SubmitField, validators,)
from wtforms.ext.sqlalchemy.fields import QuerySelectField

from matcher.filters import badge_display
from matcher.scheme.enums import ExternalObjectType, ValueType


class UploadImport(FlaskForm):
    file = FileField(validators=[FileRequired()])


class Column(Form):
    key = StringField('Column name', render_kw={'class': 'form-control',
                                                'disabled': 'disabled'})
    column_type = SelectField('Column type',
                              choices=[('', 'Unused'),
                                       ('attribute', 'Single attribute'),
                                       ('attribute_list', 'List of attributes'),
                                       ('external_object_id', 'Object ID'),
                                       ('link', 'Link ID')],
                              validators=[validators.optional()],
                              render_kw={'class': 'select2 form-control dynamic-input-controller'})

    arg_platform = SelectField('Platform',
                               render_kw={'class': 'select2 form-control dynamic-input',
                                          'data-show': 'link'})

    arg_attribute = SelectField('Attribute',
                                choices=[(str(e), badge_display(e)) for e in ValueType],
                                render_kw={'class': 'select2 form-control dynamic-input',
                                           'data-show': 'attribute attribute_list'})


class CustomFieldList(FieldList):
    def process(self, formdata, data={}):
        mapped_data = []
        for (key, value) in data.items():
            type_, _, arg = (value or '').partition('.')
            entry = {
                'key': key,
                'arg': arg,
                'column_type': type_,
                'arg_attribute': None,
                'arg_platform': None,
            }

            if type_ in ['attribute', 'attribute_list']:
                entry['arg_attribute'] = arg
            elif type_ in ['link']:
                entry['arg_platform'] = arg

            mapped_data.append(entry)

        return super(CustomFieldList, self).process(formdata, mapped_data)

    def populate_obj(self, obj, name):
        data = getattr(obj, name, {})

        for entry in self.entries:
            key = entry.key.data
            type_ = entry.column_type.data

            if type_ in ['attribute', 'attribute_list']:
                arg = entry.arg_attribute.data
            elif type_ in ['link']:
                arg = entry.arg_platform.data
            else:
                arg = None

            value = type_ if arg is None else '{type_}.{arg}'.format(type_=type_, arg=arg)

            if value:
                data[key] = value

        setattr(obj, name, data)


class EditImport(FlaskForm):
    imported_external_object_type = SelectField('New object types',
                                                choices=[(e, badge_display(e)) for e in ExternalObjectType],
                                                coerce=ExternalObjectType.coerce,
                                                render_kw={'class': 'select2 form-control'})
    platform = QuerySelectField('Platform', render_kw={'class': 'select2 form-control'})
    fields = CustomFieldList(FormField(Column, render_kw={'class': 'dynamic-input-container'}))
    save_and_import = SubmitField('Save and process', render_kw={'class': 'btn btn-primary'})
