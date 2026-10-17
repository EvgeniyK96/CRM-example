"""
Расчёт зарплаты (учебная упрощённая модель):

    оклад за отработанное = оклад × отработанные дни / норма дней месяца
    отпускные             = оклад / среднее число дней в месяце (29,3) × календарные дни отпуска
    больничные            = оклад / норма × рабочие дни болезни (100%, за счёт работодателя)
    начислено (gross)     = оклад за отработанное + отпускные + больничные + премия

    удержания с базой gross    — ОПВ, ВОСМС: gross × ставка
    облагаемый доход           = gross − удержания с базой gross − стандартный вычет (не меньше 0)
    удержания с базой taxable  — ИПН: облагаемый доход × ставка
    к выплате                  = gross − все удержания
    взносы работодателя        — gross × ставка (в расходы, сверх зарплаты)

Зарплата относится на расходы периода (директ-костинг): цеха — 7110, остальные — 7210.
"""

from decimal import ROUND_HALF_UP, Decimal

from django.conf import settings
from django.db import transaction
from django.utils import timezone

from apps.accounting import chart as C
from apps.accounting.models import JournalEntry
from apps.accounting.services import Line, record
from apps.hr import services as hr
from core.exceptions import DomainError

from .models import PayrollPeriod, PayrollRate, Payslip, PayslipLine

Status = PayrollPeriod.Status
CENT = Decimal("0.01")
ZERO = Decimal(0)


class PayrollError(DomainError):
    pass


def money(value) -> Decimal:
    return Decimal(value).quantize(CENT, ROUND_HALF_UP)


def _lock(period: PayrollPeriod) -> PayrollPeriod:
    return PayrollPeriod.objects.select_for_update().get(pk=period.pk)


def expense_account(department) -> str:
    return C.PRODUCTION_LABOR if department.is_production else C.ADMIN_EXPENSES


def compute(payslip: Payslip, rates: list[PayrollRate]) -> list[PayslipLine]:
    """Пересчитывает суммы листка (без сохранения) и возвращает строки удержаний и взносов."""
    p = payslip
    p.salary_accrued = money(p.salary * p.worked_days / p.norm_days) if p.norm_days else ZERO
    p.vacation_pay = money(p.salary / settings.PAYROLL_AVG_MONTH_DAYS * p.vacation_days)
    p.sick_pay = money(p.salary * p.sick_days / p.norm_days) if p.norm_days else ZERO
    p.gross = p.salary_accrued + p.vacation_pay + p.sick_pay + p.bonus

    lines = []

    def add(rate, base):
        lines.append(PayslipLine(payslip=p, rate=rate, payer=rate.payer, base=money(base), percent=rate.percent,
                                 amount=money(base * rate.percent / 100)))

    employee_gross = [r for r in rates if r.payer == PayrollRate.Payer.EMPLOYEE and r.base == PayrollRate.Base.GROSS]
    for rate in employee_gross:
        add(rate, p.gross)
    taxable = max(p.gross - sum((line.amount for line in lines), ZERO) - settings.PAYROLL_STANDARD_DEDUCTION, ZERO)
    for rate in rates:
        if rate.payer == PayrollRate.Payer.EMPLOYEE and rate.base == PayrollRate.Base.TAXABLE:
            add(rate, taxable)
        elif rate.payer == PayrollRate.Payer.EMPLOYER:
            add(rate, p.gross)

    p.withheld = sum((line.amount for line in lines if line.payer == PayrollRate.Payer.EMPLOYEE), ZERO)
    p.employer_total = sum((line.amount for line in lines if line.payer == PayrollRate.Payer.EMPLOYER), ZERO)
    p.net = p.gross - p.withheld
    return lines


@transaction.atomic
def calculate(period: PayrollPeriod) -> PayrollPeriod:
    """
    (Пере)расчёт ведомости по табелю: листки создаются заново,
    премии, введённые бухгалтером, сохраняются.
    """
    period = _lock(period)
    if period.status != Status.DRAFT:
        raise PayrollError("Пересчитать можно только черновик ведомости.")

    bonuses = dict(period.payslips.values_list("employee_id", "bonus"))
    period.payslips.all().delete()

    rates = list(PayrollRate.objects.filter(is_active=True))
    holiday_set = hr.holidays(period.year, period.month)
    absences = hr.month_absences(period.year, period.month)
    for employee in hr.employees_in_month(period.year, period.month):
        sheet = hr.employee_sheet(employee, period.year, period.month, holiday_set, absences.get(employee.pk, []))
        payslip = Payslip(
            period=period, employee=employee, department=employee.department, position=employee.position,
            salary=employee.salary, norm_days=sheet.norm_days, worked_days=sheet.worked_days,
            vacation_days=sheet.vacation_days, sick_days=sheet.sick_days, unpaid_days=sheet.unpaid_days,
            bonus=bonuses.get(employee.pk, ZERO),
        )
        lines = compute(payslip, rates)
        payslip.save()
        PayslipLine.objects.bulk_create(lines)

    period.calculated_at = timezone.now()
    period.save(update_fields=["calculated_at"])
    return period


@transaction.atomic
def set_bonus(payslip: Payslip, bonus: Decimal) -> Payslip:
    if payslip.period.status != Status.DRAFT:
        raise PayrollError("Ведомость уже проведена.")
    if bonus < 0:
        raise PayrollError("Премия не может быть отрицательной.")
    payslip = Payslip.objects.select_for_update().get(pk=payslip.pk)
    payslip.bonus = bonus
    payslip.lines.all().delete()
    lines = compute(payslip, list(PayrollRate.objects.filter(is_active=True)))
    payslip.save()
    PayslipLine.objects.bulk_create(lines)
    return payslip


def period_end(period: PayrollPeriod):
    days = hr.month_days(period.year, period.month)
    return days[-1]


@transaction.atomic
def post(period: PayrollPeriod, user=None) -> PayrollPeriod:
    """Проведение: начисление, удержания и взносы — проводками последним днём месяца."""
    period = _lock(period)
    if period.status != Status.DRAFT:
        raise PayrollError("Ведомость уже проведена.")
    payslips = list(period.payslips.select_related("department").prefetch_related("lines__rate"))
    if not payslips:
        raise PayrollError("Ведомость пуста — сначала рассчитайте её.")

    # Сворачиваем суммы по парам счетов, чтобы операция была читаемой
    totals: dict[tuple[str, str, str], Decimal] = {}

    def add(debit, credit, comment, amount):
        key = (debit, credit, comment)
        totals[key] = totals.get(key, ZERO) + amount

    for p in payslips:
        expense = expense_account(p.department)
        add(expense, C.PAYROLL, "Начислена заработная плата", p.gross)
        for line in p.lines.all():
            if line.payer == PayrollRate.Payer.EMPLOYEE:
                add(C.PAYROLL, line.rate.account_code, f"Удержание: {line.rate.name}", line.amount)
            else:
                add(expense, line.rate.account_code, f"Взнос работодателя: {line.rate.name}", line.amount)

    record(JournalEntry.Source.PAYROLL, period.pk, period_end(period), f"Зарплата за {period.month:02d}.{period.year}",
           [Line(d, c, amount, comment=comment) for (d, c, comment), amount in totals.items()], user)

    period.status = Status.POSTED
    period.posted_at = timezone.now()
    period.save(update_fields=["status", "posted_at"])
    return period


@transaction.atomic
def unpost(period: PayrollPeriod) -> PayrollPeriod:
    """Отмена проведения (пока зарплата не выплачена): проводки удаляются, ведомость снова черновик."""
    period = _lock(period)
    if period.status != Status.POSTED:
        raise PayrollError("Отменить можно только проведённую и не выплаченную ведомость.")
    JournalEntry.objects.filter(source_type=JournalEntry.Source.PAYROLL, source_id=period.pk).delete()
    period.status = Status.DRAFT
    period.posted_at = None
    period.save(update_fields=["status", "posted_at"])
    return period


@transaction.atomic
def pay(period: PayrollPeriod, *, method: str = "bank", user=None) -> PayrollPeriod:
    """Выплата: Дт 3350 — Кт 1030 (или 1010) на сумму к выплате."""
    period = _lock(period)
    if period.status != Status.POSTED:
        raise PayrollError("Выплатить можно только проведённую ведомость.")
    net = sum((p.net for p in period.payslips.all()), ZERO)
    money_account = C.CASH if method == "cash" else C.BANK
    today = timezone.localdate()
    record(JournalEntry.Source.PAYROLL_PAYMENT, period.pk, today, f"Выплата зарплаты за {period.month:02d}.{period.year}",
           [Line(C.PAYROLL, money_account, net, comment="Перечислено сотрудникам")], user)
    period.status = Status.PAID
    period.paid_at = timezone.now()
    period.save(update_fields=["status", "paid_at"])
    return period
