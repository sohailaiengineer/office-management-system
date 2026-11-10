from flask_wtf import FlaskForm
from flask_wtf.file import FileField, FileAllowed
from wtforms import StringField, TextAreaField, SelectField, BooleanField, SubmitField
from wtforms.validators import DataRequired, Length, Optional

class AnnouncementForm(FlaskForm):
    title = StringField('Announcement Title', validators=[DataRequired(), Length(max=200)])
    content = TextAreaField('Announcement Body / Notice', validators=[DataRequired(), Length(min=10)])
    target_audience = SelectField('Target Audience', choices=[
        ('All', 'Company-Wide (All Employees)'),
        ('Department', 'Specific Department'),
        ('Management', 'Leadership / Management Only')
    ], default='All', validators=[DataRequired()])
    department_id = SelectField('Target Department', coerce=int, validators=[Optional()])
    is_pinned = BooleanField('Pin to Top of Noticeboard')
    submit = SubmitField('Broadcast Announcement')


class DirectMessageForm(FlaskForm):
    recipient_type = SelectField('Recipient Category', choices=[
        ('specific', 'Specific Person / Colleague'),
        ('admin', 'Super Admin'),
        ('hr', 'HR Manager'),
        ('dept_manager', 'Department Manager')
    ], default='specific', validators=[Optional()])
    recipient_id = SelectField('Select Recipient', coerce=int, validators=[DataRequired()])
    subject = StringField('Subject', validators=[DataRequired(), Length(max=200)])
    body = TextAreaField('Message Content', validators=[DataRequired(), Length(min=2)])
    attachment = FileField('Attach File (Optional)', validators=[
        Optional(),
        FileAllowed(['pdf', 'docx', 'doc', 'xlsx', 'xls', 'csv', 'png', 'jpg', 'jpeg', 'txt'], 'Permitted: PDF, Word, Excel, CSV, Images')
    ])
    submit = SubmitField('Send Message')
