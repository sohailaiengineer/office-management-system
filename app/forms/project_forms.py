from flask_wtf import FlaskForm
from wtforms import StringField, TextAreaField, SelectField, DecimalField, DateField, IntegerField, SubmitField
from wtforms.validators import DataRequired, Length, NumberRange, Optional

class ProjectForm(FlaskForm):
    name = StringField('Project Name', validators=[DataRequired(), Length(max=150)])
    code = StringField('Project Code', validators=[DataRequired(), Length(max=50)])
    client_id = SelectField('Client', coerce=int, validators=[Optional()])
    department_id = SelectField('Department', coerce=int, validators=[Optional()])
    lead_id = SelectField('Project Lead', coerce=int, validators=[Optional()])
    start_date = DateField('Start Date', validators=[DataRequired()])
    deadline = DateField('Target Deadline', validators=[DataRequired()])
    budget = DecimalField('Budget ($)', places=2, default=0.00, validators=[DataRequired(), NumberRange(min=0)])
    priority = SelectField('Priority', choices=[
        ('Low', 'Low'), ('Medium', 'Medium'), ('High', 'High'), ('Urgent', 'Urgent')
    ], default='Medium')
    project_status = SelectField('Status', choices=[
        ('Planning', 'Planning'), ('In-Progress', 'In-Progress'),
        ('On-Hold', 'On-Hold'), ('Completed', 'Completed'), ('Cancelled', 'Cancelled')
    ], default='Planning')
    description = TextAreaField('Scope & Description', validators=[Optional()])
    submit = SubmitField('Save Project')


class TaskForm(FlaskForm):
    project_id = SelectField('Project', coerce=int, validators=[DataRequired()])
    title = StringField('Task Title', validators=[DataRequired(), Length(max=200)])
    assigned_employee_id = SelectField('Assignee', coerce=int, validators=[Optional()])
    priority = SelectField('Priority', choices=[
        ('Low', 'Low'), ('Medium', 'Medium'), ('High', 'High'), ('Urgent', 'Urgent')
    ], default='Medium')
    task_status = SelectField('Task Status', choices=[
        ('To-Do', 'To-Do'), ('In-Progress', 'In-Progress'),
        ('Review', 'Review'), ('Completed', 'Completed')
    ], default='To-Do')
    estimated_hours = DecimalField('Estimated Hours', places=2, default=0.00, validators=[DataRequired(), NumberRange(min=0)])
    start_date = DateField('Start Date', validators=[Optional()])
    due_date = DateField('Due Date', validators=[DataRequired()])
    description = TextAreaField('Task Specifications', validators=[Optional()])
    submit = SubmitField('Save Task')


class TaskCommentForm(FlaskForm):
    comment = TextAreaField('Post an Update or Comment', validators=[DataRequired(), Length(min=2)])
    submit = SubmitField('Post Comment')
