from flask_wtf import FlaskForm
from wtforms import StringField, TextAreaField, SelectField, SubmitField
from wtforms.validators import DataRequired, Email, Length, Optional

class ClientForm(FlaskForm):
    company_name = StringField('Company Name', validators=[DataRequired(), Length(max=150)])
    client_code = StringField('Client Code', validators=[DataRequired(), Length(max=50)])
    industry = StringField('Industry Sector', validators=[Optional(), Length(max=100)])
    email = StringField('Corporate Email', validators=[Optional(), Email(), Length(max=120)])
    phone = StringField('Phone Number', validators=[Optional(), Length(max=30)])
    website = StringField('Website URL', validators=[Optional(), Length(max=150)])
    address = TextAreaField('Physical Address', validators=[Optional(), Length(max=255)])
    country = StringField('Country', default='USA', validators=[DataRequired(), Length(max=100)])
    submit = SubmitField('Save Client')


class ClientInteractionForm(FlaskForm):
    interaction_type = SelectField('Interaction Type', choices=[
        ('Meeting', 'Meeting'), ('Call', 'Phone Call'),
        ('Email', 'Email Correspondence'), ('Demo', 'Product Demo')
    ], default='Meeting', validators=[DataRequired()])
    conducted_by_id = SelectField('Conducted By', coerce=int, validators=[Optional()])
    summary = TextAreaField('Discussion Summary & Action Items', validators=[DataRequired(), Length(min=5)])
    submit = SubmitField('Log Interaction')

