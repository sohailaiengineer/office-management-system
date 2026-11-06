from flask_wtf import FlaskForm
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
    recipient_id = SelectField('Recipient', coerce=int, validators=[DataRequired()])
    subject = StringField('Subject', validators=[DataRequired(), Length(max=200)])
    body = TextAreaField('Message Content', validators=[DataRequired(), Length(min=5)])
    submit = SubmitField('Send Message')

