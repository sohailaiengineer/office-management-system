from flask_wtf import FlaskForm
from flask_wtf.file import FileField, FileAllowed
from wtforms import StringField, TextAreaField, SelectField, BooleanField, SubmitField
from wtforms.validators import DataRequired, Length, Optional

class DocumentUploadForm(FlaskForm):
    title = StringField('Document Title', validators=[DataRequired(), Length(max=200)])
    category_id = SelectField('Category', coerce=int, validators=[DataRequired()])
    department_id = SelectField('Department (Optional)', coerce=int, validators=[Optional()])
    description = TextAreaField('Description / Notes', validators=[Optional()])
    is_confidential = BooleanField('Confidential Document')
    file = FileField('Attachment File', validators=[
        FileAllowed(['pdf', 'docx', 'xlsx', 'csv', 'txt', 'png', 'jpg', 'jpeg'], 'Supported file formats: PDF, DOCX, XLSX, CSV, TXT, Images.')
    ])
    submit = SubmitField('Upload Document')


class DocumentCategoryForm(FlaskForm):
    name = StringField('Category Name', validators=[DataRequired(), Length(max=100)])
    code = StringField('Category Code', validators=[DataRequired(), Length(max=30)])
    description = TextAreaField('Description', validators=[Optional(), Length(max=255)])
    submit = SubmitField('Save Category')

