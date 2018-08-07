from flask_wtf import FlaskForm
from flask_wtf.file import FileField, FileRequired


class UploadImport(FlaskForm):
    file = FileField(validators=[FileRequired()])
