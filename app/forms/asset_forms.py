from flask_wtf import FlaskForm
from wtforms import StringField, TextAreaField, SelectField, DecimalField, DateField, SubmitField
from wtforms.validators import DataRequired, Length, NumberRange, Optional

class AssetForm(FlaskForm):
    category_id = SelectField('Asset Category', coerce=int, validators=[DataRequired()])
    name = StringField('Asset Name', validators=[DataRequired(), Length(max=150)])
    asset_tag = StringField('Asset Tag / Barcode', validators=[DataRequired(), Length(max=50)])
    serial_number = StringField('Serial Number', validators=[Optional(), Length(max=100)])
    purchase_date = DateField('Purchase Date', validators=[DataRequired()])
    purchase_cost = DecimalField('Purchase Cost ($)', places=2, default=0.00, validators=[DataRequired(), NumberRange(min=0)])
    warranty_expiry = DateField('Warranty Expiry Date', validators=[Optional()])
    condition = SelectField('Condition', choices=[
        ('New', 'New'), ('Good', 'Good'), ('Fair', 'Fair'), ('Damaged', 'Damaged')
    ], default='Good')
    asset_status = SelectField('Status', choices=[
        ('Available', 'Available'), ('Assigned', 'Assigned'),
        ('Under-Maintenance', 'Under-Maintenance'), ('Disposed', 'Disposed')
    ], default='Available')
    submit = SubmitField('Save Asset')


class AssetAssignmentForm(FlaskForm):
    employee_id = SelectField('Assign to Employee', coerce=int, validators=[DataRequired()])
    assigned_date = DateField('Assignment Date', validators=[DataRequired()])
    condition_at_assign = SelectField('Condition at Handover', choices=[
        ('New', 'New'), ('Good', 'Good'), ('Fair', 'Fair')
    ], default='Good')
    submit = SubmitField('Assign Asset')


class AssetRequestForm(FlaskForm):
    category_id = SelectField('Requested Category', coerce=int, validators=[DataRequired()])
    priority = SelectField('Priority', choices=[
        ('Low', 'Low'), ('Medium', 'Medium'), ('High', 'High')
    ], default='Medium')
    reason = TextAreaField('Justification & Requirements', validators=[DataRequired(), Length(min=10)])
    submit = SubmitField('Submit Equipment Request')
