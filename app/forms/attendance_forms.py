from flask_wtf import FlaskForm
from wtforms import StringField, TimeField, IntegerField, BooleanField, DateField, SubmitField
from wtforms.validators import DataRequired, Length, NumberRange

class ShiftForm(FlaskForm):
    name = StringField('Shift Name', validators=[DataRequired(), Length(max=100)])
    start_time = TimeField('Start Time', validators=[DataRequired()])
    end_time = TimeField('End Time', validators=[DataRequired()])
    grace_minutes = IntegerField('Grace Period (Minutes)', default=15, validators=[DataRequired(), NumberRange(min=0, max=60)])
    is_night_shift = BooleanField('Night Shift')
    submit = SubmitField('Save Shift')


class HolidayForm(FlaskForm):
    name = StringField('Holiday Name', validators=[DataRequired(), Length(max=150)])
    start_date = DateField('Start Date', validators=[DataRequired()])
    end_date = DateField('End Date', validators=[DataRequired()])
    is_recurring = BooleanField('Recurring Annually')
    submit = SubmitField('Save Holiday')
