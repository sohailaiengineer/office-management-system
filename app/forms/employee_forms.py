from flask_wtf import FlaskForm
from wtforms import StringField, TextAreaField, SelectField, DecimalField, DateField, PasswordField, BooleanField, SubmitField
from wtforms.validators import DataRequired, Email, Length, Optional, NumberRange

class EmployeeForm(FlaskForm):
    # User Details
    first_name = StringField('First Name', validators=[DataRequired(), Length(max=80)])
    last_name = StringField('Last Name', validators=[DataRequired(), Length(max=80)])
    email = StringField('Email Address', validators=[DataRequired(), Email(), Length(max=120)])
    username = StringField('Username', validators=[DataRequired(), Length(min=3, max=80)])
    phone = StringField('Phone Number', validators=[Optional(), Length(max=30)])
    role_id = SelectField('User Role', coerce=int, validators=[Optional()])
    password = PasswordField('Account Password', validators=[Optional(), Length(min=6, max=100)])
    auto_generate_password = BooleanField('Auto-generate secure temporary password if left empty', default=True)
    send_activation_email = BooleanField('Send Welcome & Account Activation Email', default=True)
    
    # Employment Details
    emp_code = StringField('Employee Code', validators=[DataRequired(), Length(max=30)])
    department_id = SelectField('Department', coerce=int, validators=[DataRequired()])
    designation_id = SelectField('Designation', coerce=int, validators=[DataRequired()])
    manager_id = SelectField('Reporting Manager', coerce=int, validators=[Optional()])
    employment_type = SelectField('Employment Type', choices=[
        ('Full-Time', 'Full-Time'), ('Part-Time', 'Part-Time'),
        ('Contract', 'Contract'), ('Intern', 'Intern')
    ], validators=[DataRequired()])
    date_of_joining = DateField('Date of Joining', validators=[DataRequired()])
    basic_salary = DecimalField('Basic Salary ($)', places=2, validators=[DataRequired(), NumberRange(min=0)])
    status = SelectField('Status', choices=[('Active', 'Active'), ('Deactive', 'Deactive')], default='Active')

    # Profile Details
    gender = SelectField('Gender', choices=[('Male', 'Male'), ('Female', 'Female'), ('Other', 'Other')], validators=[Optional()])
    marital_status = SelectField('Marital Status', choices=[('Single', 'Single'), ('Married', 'Married'), ('Divorced', 'Divorced')], validators=[Optional()])
    blood_group = SelectField('Blood Group', choices=[
        ('', 'Select...'), ('A+', 'A+'), ('A-', 'A-'), ('B+', 'B+'), ('B-', 'B-'),
        ('O+', 'O+'), ('O-', 'O-'), ('AB+', 'AB+'), ('AB-', 'AB-')
    ], validators=[Optional()])
    dob = DateField('Date of Birth', validators=[Optional()])
    nationality = StringField('Nationality', default='American', validators=[Optional(), Length(max=80)])
    nid_passport = StringField('National ID / Passport', validators=[Optional(), Length(max=100)])
    bio = TextAreaField('Professional Biography', validators=[Optional()])
    
    submit = SubmitField('Save Employee')


class DepartmentForm(FlaskForm):
    name = StringField('Department Name', validators=[DataRequired(), Length(max=100)])
    code = StringField('Department Code', validators=[DataRequired(), Length(max=30)])
    manager_id = SelectField('Department Manager', coerce=int, validators=[Optional()])
    budget = DecimalField('Annual Budget ($)', places=2, default=0.00, validators=[DataRequired(), NumberRange(min=0)])
    description = TextAreaField('Description', validators=[Optional()])
    submit = SubmitField('Save Department')


class DesignationForm(FlaskForm):
    title = StringField('Designation Title', validators=[DataRequired(), Length(max=100)])
    code = StringField('Designation Code', validators=[DataRequired(), Length(max=30)])
    department_id = SelectField('Department', coerce=int, validators=[DataRequired()])
    salary_grade = StringField('Salary Grade', validators=[Optional(), Length(max=50)])
    min_salary = DecimalField('Minimum Salary ($)', places=2, default=0.00, validators=[Optional(), NumberRange(min=0)])
    max_salary = DecimalField('Maximum Salary ($)', places=2, default=0.00, validators=[Optional(), NumberRange(min=0)])
    submit = SubmitField('Save Designation')
