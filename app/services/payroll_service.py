from datetime import datetime, date
from decimal import Decimal
from app.extensions import db
from app.models.employee import Employee
from app.models.payroll import Payroll, PayrollDetail, EmployeeSalary, Bonus, Deduction
from app.models.attendance import Attendance

def calculate_employee_salary_components(employee_id, gross_salary=None):
    """
    Calculates detailed salary components for an employee according to their structure.
    Returns dictionary with breakdown: basic, house_rent, medical, transport, tax, gross.
    """
    emp_salary = EmployeeSalary.active_query().filter_by(employee_id=employee_id).first()
    if emp_salary:
        return {
            'basic': emp_salary.basic_salary,
            'house_rent': emp_salary.house_rent,
            'medical': emp_salary.medical_allowance,
            'transport': emp_salary.transport_allowance,
            'gross': emp_salary.gross_salary
        }
    
    emp = Employee.active_query().get(employee_id)
    base = emp.basic_salary if emp else Decimal('3000.00')
    hra = (base * Decimal('0.20')).quantize(Decimal('0.01'))
    med = Decimal('200.00')
    transport = Decimal('150.00')
    gross = base + hra + med + transport

    return {
        'basic': base,
        'house_rent': hra,
        'medical': med,
        'transport': transport,
        'gross': gross
    }

def generate_monthly_payroll(month, year, user_id=None):
    """
    Generates a full payroll batch for active employees for the given month and year.
    """
    title = f"Payroll - {date(year, month, 1).strftime('%B %Y')}"
    existing = Payroll.active_query().filter_by(month=month, year=year).first()
    if existing:
        return existing, False, "Payroll for this month already exists."

    payroll = Payroll(
        month=month,
        year=year,
        title=title,
        total_amount=Decimal('0.00'),
        total_deductions=Decimal('0.00'),
        net_amount=Decimal('0.00'),
        payroll_status='Draft',
        created_by=user_id,
        updated_by=user_id
    )
    db.session.add(payroll)
    db.session.flush()

    active_employees = Employee.active_query().all()
    total_gross = Decimal('0.00')
    total_ded = Decimal('0.00')

    for emp in active_employees:
        comps = calculate_employee_salary_components(emp.id)
        basic = comps['basic']
        allowances = comps['house_rent'] + comps['medical'] + comps['transport']
        
        # Calculate absent deductions if any
        # Check absent days in the target month
        absent_count = Attendance.active_query().filter(
            Attendance.employee_id == emp.id,
            Attendance.attendance_status == 'Absent',
            db.extract('month', Attendance.date) == month,
            db.extract('year', Attendance.date) == year
        ).count()
        per_day_rate = (basic / Decimal('30')).quantize(Decimal('0.01'))
        absent_deduction = per_day_rate * Decimal(absent_count)

        # Standard tax deduction 5%
        tax_deduction = (comps['gross'] * Decimal('0.05')).quantize(Decimal('0.01'))
        emp_deductions = tax_deduction + absent_deduction
        net = comps['gross'] - emp_deductions

        detail = PayrollDetail(
            payroll_id=payroll.id,
            employee_id=emp.id,
            basic=basic,
            allowances=allowances,
            overtime_amount=Decimal('0.00'),
            bonuses_total=Decimal('0.00'),
            deductions_total=emp_deductions,
            net_salary=net,
            payment_status='Unpaid',
            created_by=user_id,
            updated_by=user_id
        )
        db.session.add(detail)
        total_gross += comps['gross']
        total_ded += emp_deductions

    payroll.total_amount = total_gross
    payroll.total_deductions = total_ded
    payroll.net_amount = total_gross - total_ded

    db.session.commit()
    return payroll, True, "Monthly payroll generated successfully."
