from flask_wtf import FlaskForm
from wtforms import StringField, TextAreaField, SelectField, DecimalField, DateField, SubmitField
from wtforms.validators import DataRequired, Length, NumberRange, Optional

class ExpenseForm(FlaskForm):
    category_id = SelectField('Expense Category', coerce=int, validators=[DataRequired()])
    title = StringField('Expense Title', validators=[DataRequired(), Length(max=150)])
    amount = DecimalField('Amount ($)', places=2, validators=[DataRequired(), NumberRange(min=0.01)])
    expense_date = DateField('Expense Date', validators=[DataRequired()])
    payment_method = SelectField('Payment Method', choices=[
        ('Cash', 'Cash'), ('Credit Card', 'Credit Card'),
        ('Bank Transfer', 'Bank Transfer'), ('Corporate Card', 'Corporate Card')
    ], validators=[DataRequired()])
    description = TextAreaField('Description / Purpose', validators=[Optional()])
    submit = SubmitField('Submit Expense')


class InvoiceForm(FlaskForm):
    invoice_number = StringField('Invoice Number', validators=[DataRequired(), Length(max=50)])
    client_id = SelectField('Client', coerce=int, validators=[DataRequired()])
    issue_date = DateField('Issue Date', validators=[DataRequired()])
    due_date = DateField('Due Date', validators=[DataRequired()])
    subtotal = DecimalField('Subtotal ($)', places=2, validators=[DataRequired(), NumberRange(min=0)])
    tax_amount = DecimalField('Tax Amount ($)', places=2, default=0.00, validators=[DataRequired(), NumberRange(min=0)])
    total_amount = DecimalField('Total Amount ($)', places=2, validators=[DataRequired(), NumberRange(min=0)])
    notes = TextAreaField('Terms & Notes', validators=[Optional()])
    submit = SubmitField('Create Invoice')
