from flask_wtf import FlaskForm
from wtforms import StringField, SelectField, DecimalField, IntegerField, DateField, SubmitField
from wtforms.validators import DataRequired, Length, NumberRange, Optional

class ProcessPayrollForm(FlaskForm):
    month = SelectField('Month', coerce=int, choices=[
        (1, 'January'), (2, 'February'), (3, 'March'), (4, 'April'),
        (5, 'May'), (6, 'June'), (7, 'July'), (8, 'August'),
        (9, 'September'), (10, 'October'), (11, 'November'), (12, 'December')
    ], validators=[DataRequired()])
    year = IntegerField('Year', validators=[DataRequired(), NumberRange(min=2020, max=2030)])
    submit = SubmitField('Calculate & Generate Payroll')


class IndividualSalaryForm(FlaskForm):
    employee_id = SelectField('Employee', coerce=int, validators=[DataRequired()])
    month = SelectField('Pay Period Month', coerce=int, choices=[
        (1, 'January'), (2, 'February'), (3, 'March'), (4, 'April'),
        (5, 'May'), (6, 'June'), (7, 'July'), (8, 'August'),
        (9, 'September'), (10, 'October'), (11, 'November'), (12, 'December')
    ], validators=[DataRequired()])
    year = IntegerField('Pay Period Year', validators=[DataRequired(), NumberRange(min=2020, max=2030)])
    basic = DecimalField('Basic Salary ($)', places=2, default=0.00, validators=[DataRequired(), NumberRange(min=0)])
    allowances = DecimalField('Allowances (HRA / Medical / Transport) ($)', places=2, default=0.00, validators=[Optional(), NumberRange(min=0)])
    bonuses_total = DecimalField('Bonuses ($)', places=2, default=0.00, validators=[Optional(), NumberRange(min=0)])
    overtime_amount = DecimalField('Overtime ($)', places=2, default=0.00, validators=[Optional(), NumberRange(min=0)])
    deductions_total = DecimalField('Deductions (Tax / Insurance / Leaves) ($)', places=2, default=0.00, validators=[Optional(), NumberRange(min=0)])
    payment_status = SelectField('Payment Status', choices=[
        ('Pending', 'Pending'),
        ('Paid', 'Paid'),
        ('Unpaid', 'Unpaid')
    ], default='Pending', validators=[DataRequired()])
    payment_method = SelectField('Payment Method', choices=[
        ('Bank Transfer', 'Direct Bank Transfer'),
        ('Corporate Cheque', 'Corporate Cheque'),
        ('Cash', 'Cash Disbursement')
    ], default='Bank Transfer', validators=[DataRequired()])
    submit = SubmitField('Generate Employee Salary Slip')


class BonusForm(FlaskForm):
    employee_id = SelectField('Employee', coerce=int, validators=[DataRequired()])
    bonus_type = SelectField('Bonus Type', choices=[
        ('Performance', 'Performance'), ('Festival', 'Festival'),
        ('Annual', 'Annual'), ('Referral', 'Referral')
    ], validators=[DataRequired()])
    amount = DecimalField('Bonus Amount ($)', places=2, validators=[DataRequired(), NumberRange(min=1)])
    reason = StringField('Reason / Notes', validators=[Optional(), Length(max=255)])
    bonus_date = DateField('Award Date', validators=[DataRequired()])
    submit = SubmitField('Record Bonus')


class DeductionForm(FlaskForm):
    employee_id = SelectField('Employee', coerce=int, validators=[DataRequired()])
    deduction_type = SelectField('Deduction Type', choices=[
        ('Tax', 'Tax Adjustment'), ('Fine', 'Disciplinary Fine'),
        ('Loan', 'Loan Repayment'), ('Insurance', 'Insurance Premium')
    ], validators=[DataRequired()])
    amount = DecimalField('Deduction Amount ($)', places=2, validators=[DataRequired(), NumberRange(min=1)])
    reason = StringField('Reason / Description', validators=[Optional(), Length(max=255)])
    deduction_date = DateField('Deduction Date', validators=[DataRequired()])
    submit = SubmitField('Record Deduction')
