from flask_wtf import FlaskForm
from flask_wtf.file import FileField, FileAllowed
from wtforms import StringField, TextAreaField, SelectField, DateField, IntegerField, BooleanField, SubmitField
from wtforms.validators import DataRequired, Length, NumberRange, Optional

class LeaveRequestForm(FlaskForm):
    leave_type_id = SelectField('Leave Type', coerce=int, validators=[DataRequired()])
    start_date = DateField('Start Date', validators=[DataRequired()])
    end_date = DateField('End Date', validators=[DataRequired()])
    reason = TextAreaField('Reason for Leave', validators=[DataRequired(), Length(min=10)])
    supporting_document = FileField('Supporting Document (Optional)', validators=[
        Optional(),
        FileAllowed(['pdf', 'jpg', 'jpeg', 'png', 'docx', 'doc'], 'Permitted document types: PDF, Word, Images')
    ])
    submit = SubmitField('Submit Leave Application')


class LeaveTypeForm(FlaskForm):
    name = StringField('Leave Type Name', validators=[DataRequired(), Length(max=100)])
    code = StringField('Code', validators=[DataRequired(), Length(max=30)])
    max_days_per_year = IntegerField('Max Days Allowed Per Year', default=15, validators=[DataRequired(), NumberRange(min=1, max=365)])
    is_paid = BooleanField('Is Paid Leave', default=True)
    carry_forward = BooleanField('Allow Carry Forward')
    submit = SubmitField('Save Leave Type')


class LeaveApprovalForm(FlaskForm):
    action = SelectField('Action', choices=[('Approved', 'Approve'), ('Rejected', 'Reject')], validators=[DataRequired()])
    comments = TextAreaField('Reviewer Comments', validators=[Optional()])
    submit = SubmitField('Confirm Decision')
