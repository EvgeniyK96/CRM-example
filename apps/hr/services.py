"""Кадры: приказы, отсутствия, производственный календарь и табель."""

import calendar
from dataclasses import dataclass, field
from datetime import date, timedelta

from django.db import transaction

from core.exceptions import DomainError

from .models import Absence, Employee, Holiday, HROrder

WEEKEND = {5, 6}  # суббота, воскресенье


class HRError(DomainError):
    pass


# --- Приказы -----------------------------------------------------------------


def _lock(employee: Employee) -> Employee:
    return Employee.objects.select_for_update().select_related("department", "position").get(pk=employee.pk)


@transaction.atomic
def hire(employee: Employee, user=None) -> HROrder:
    """Приказ о приёме для только что созданной карточки сотрудника."""
    return HROrder.objects.create(
        kind=HROrder.Kind.HIRE, employee=employee, date=employee.hire_date, to_department=employee.department,
        to_position=employee.position, to_salary=employee.salary, created_by=user,
    )


@transaction.atomic
def issue_order(employee: Employee, kind: str, on_date: date, *, department=None, position=None, salary=None,
                reason: str = "", user=None) -> HROrder:
    """Перевод, изменение оклада или увольнение. Изменения применяются к карточке сразу (учебное упрощение)."""
    employee = _lock(employee)
    if employee.status == Employee.Status.FIRED:
        raise HRError("Сотрудник уже уволен.")
    if on_date < employee.hire_date:
        raise HRError("Дата приказа раньше даты приёма.")

    order = HROrder(kind=kind, employee=employee, date=on_date, reason=reason, created_by=user,
                    from_department=employee.department, from_position=employee.position, from_salary=employee.salary)

    if kind == HROrder.Kind.TRANSFER:
        if not department and not position:
            raise HRError("Укажите новое подразделение или должность.")
        employee.department = department or employee.department
        employee.position = position or employee.position
        if salary:
            employee.salary = salary
    elif kind == HROrder.Kind.SALARY:
        if not salary or salary <= 0:
            raise HRError("Укажите новый оклад.")
        employee.salary = salary
    elif kind == HROrder.Kind.DISMISSAL:
        employee.fire_date = on_date
        employee.status = Employee.Status.FIRED
        if employee.user_id:  # уволенный не должен входить в систему
            employee.user.is_active = False
            employee.user.save(update_fields=["is_active"])
    else:
        raise HRError("Приём оформляется созданием карточки сотрудника.")

    employee.save()
    order.to_department, order.to_position, order.to_salary = employee.department, employee.position, employee.salary
    order.save()
    return order


# --- Отсутствия --------------------------------------------------------------


def check_absence(employee: Employee, date_from: date, date_to: date, exclude_pk=None) -> None:
    if date_to < date_from:
        raise HRError("Дата окончания раньше даты начала.")
    if date_from < employee.hire_date or (employee.fire_date and date_to > employee.fire_date):
        raise HRError("Период вне срока работы сотрудника.")
    overlapping = Absence.objects.filter(employee=employee, date_from__lte=date_to, date_to__gte=date_from)
    if exclude_pk:
        overlapping = overlapping.exclude(pk=exclude_pk)
    if other := overlapping.first():
        raise HRError(f"Пересекается с «{other.get_kind_display()}» {other.date_from:%d.%m}–{other.date_to:%d.%m}.")


# --- Календарь и табель ----------------------------------------------------------


def month_days(year: int, month: int) -> list[date]:
    return [date(year, month, d) for d in range(1, calendar.monthrange(year, month)[1] + 1)]


def holidays(year: int, month: int) -> set[date]:
    return set(Holiday.objects.filter(date__year=year, date__month=month).values_list("date", flat=True))


def is_workday(day: date, holiday_set: set[date]) -> bool:
    return day.weekday() not in WEEKEND and day not in holiday_set


# Коды табеля
WORK, OFF, VACATION, SICK, TRIP, UNPAID, NOT_EMPLOYED = "Я", "В", "О", "Б", "К", "НН", ""
ABSENCE_CODES = {
    Absence.Kind.VACATION: VACATION, Absence.Kind.SICK: SICK, Absence.Kind.BUSINESS_TRIP: TRIP,
    Absence.Kind.UNPAID: UNPAID,
}


@dataclass
class MonthSheet:
    """Табель сотрудника за месяц и итоги для расчёта зарплаты."""

    cells: list[str]
    norm_days: int  # рабочих дней в месяце по календарю
    worked_days: int = 0  # явки + командировки
    vacation_days: int = 0  # календарные дни отпуска (отпускные считаются по календарным)
    sick_days: int = 0  # рабочие дни болезни
    unpaid_days: int = 0  # рабочие дни без содержания
    absences: list = field(default_factory=list)


def employee_sheet(employee: Employee, year: int, month: int, holiday_set: set[date], absences: list[Absence]) -> MonthSheet:
    days = month_days(year, month)
    sheet = MonthSheet(cells=[], norm_days=sum(is_workday(d, holiday_set) for d in days))
    for day in days:
        employed = employee.hire_date <= day and (not employee.fire_date or day <= employee.fire_date)
        absence = next((a for a in absences if a.date_from <= day <= a.date_to), None)
        workday = is_workday(day, holiday_set)
        if not employed:
            code = NOT_EMPLOYED
        elif absence and absence.kind == Absence.Kind.VACATION:
            code = VACATION
            sheet.vacation_days += 1
        elif not workday:
            code = OFF
        elif absence:
            code = ABSENCE_CODES[absence.kind]
            if code == TRIP:
                sheet.worked_days += 1
            elif code == SICK:
                sheet.sick_days += 1
            else:
                sheet.unpaid_days += 1
        else:
            code = WORK
            sheet.worked_days += 1
        sheet.cells.append(code)
    return sheet


def employees_in_month(year: int, month: int, department_id=None):
    first, last = date(year, month, 1), date(year, month, calendar.monthrange(year, month)[1])
    employees = Employee.objects.filter(hire_date__lte=last).exclude(fire_date__lt=first).select_related(
        "department", "position"
    )
    if department_id:
        employees = employees.filter(department_id=department_id)
    return employees.order_by("department__name", "last_name")


def month_absences(year: int, month: int) -> dict[int, list[Absence]]:
    first, last = date(year, month, 1), date(year, month, calendar.monthrange(year, month)[1])
    by_employee: dict[int, list[Absence]] = {}
    for a in Absence.objects.filter(date_from__lte=last, date_to__gte=first):
        by_employee.setdefault(a.employee_id, []).append(a)
    return by_employee


def timesheet(year: int, month: int, department_id=None) -> dict:
    """Табель учёта рабочего времени за месяц (строится из календаря и отсутствий)."""
    holiday_set = holidays(year, month)
    absences = month_absences(year, month)
    days = month_days(year, month)
    rows = []
    for employee in employees_in_month(year, month, department_id):
        sheet = employee_sheet(employee, year, month, holiday_set, absences.get(employee.pk, []))
        rows.append({
            "employee": employee.pk, "full_name": employee.full_name, "department_name": employee.department.name,
            "position_name": employee.position.name, "cells": sheet.cells, "worked_days": sheet.worked_days,
            "vacation_days": sheet.vacation_days, "sick_days": sheet.sick_days, "unpaid_days": sheet.unpaid_days,
        })
    return {
        "year": year, "month": month,
        "days": [{"day": d.day, "weekday": d.weekday(), "workday": is_workday(d, holiday_set),
                  "holiday": d in holiday_set} for d in days],
        "norm_days": sum(is_workday(d, holiday_set) for d in days),
        "rows": rows,
    }


def previous_month(day: date) -> tuple[int, int]:
    prev = day.replace(day=1) - timedelta(days=1)
    return prev.year, prev.month

