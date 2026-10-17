from django.conf import settings
from django.db import models
from django.db.models import Q


class PayrollRate(models.Model):
    """
    Ставка удержания из зарплаты или взноса работодателя.
    Учебные упрощённые ставки по образцу РК; бухгалтер может их изменить.
    """

    class Payer(models.TextChoices):
        EMPLOYEE = "employee", "Удерживается из зарплаты"
        EMPLOYER = "employer", "Платит работодатель"

    class Base(models.TextChoices):
        GROSS = "gross", "От начисленной суммы"
        TAXABLE = "taxable", "От облагаемого дохода (за вычетом удержаний и стандартного вычета)"

    code = models.CharField("Код", max_length=20, unique=True)
    name = models.CharField("Название", max_length=120)
    payer = models.CharField("Кто платит", max_length=10, choices=Payer.choices)
    base = models.CharField("База", max_length=10, choices=Base.choices, default=Base.GROSS)
    percent = models.DecimalField("Ставка, %", max_digits=5, decimal_places=2)
    account_code = models.CharField("Счёт обязательства", max_length=10)
    is_active = models.BooleanField("Применяется", default=True)

    class Meta:
        verbose_name = "Ставка удержания / взноса"
        verbose_name_plural = "Ставки удержаний и взносов"
        ordering = ["payer", "code"]
        constraints = [models.CheckConstraint(condition=Q(percent__gte=0, percent__lte=100), name="rate_percent_range")]

    def __str__(self):
        return f"{self.name} {self.percent}%"


class PayrollPeriod(models.Model):
    """Расчётная ведомость за месяц: черновик → проведена (проводки) → выплачена."""

    class Status(models.TextChoices):
        DRAFT = "draft", "Черновик"
        POSTED = "posted", "Проведена"
        PAID = "paid", "Выплачена"

    year = models.PositiveIntegerField("Год")
    month = models.PositiveSmallIntegerField("Месяц")
    status = models.CharField("Статус", max_length=10, choices=Status.choices, default=Status.DRAFT)
    calculated_at = models.DateTimeField("Рассчитана", null=True, blank=True)
    posted_at = models.DateTimeField("Проведена", null=True, blank=True)
    paid_at = models.DateTimeField("Выплачена", null=True, blank=True)
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, verbose_name="Автор", null=True, blank=True,
                                   on_delete=models.SET_NULL, related_name="+")

    class Meta:
        verbose_name = "Расчётная ведомость"
        verbose_name_plural = "Расчётные ведомости"
        ordering = ["-year", "-month"]
        constraints = [
            models.UniqueConstraint(fields=["year", "month"], name="unique_payroll_month"),
            models.CheckConstraint(condition=Q(month__gte=1, month__lte=12), name="payroll_month_range"),
        ]

    def __str__(self):
        return f"Зарплата за {self.month:02d}.{self.year}"

    @property
    def is_editable(self):
        return self.status == self.Status.DRAFT


class Payslip(models.Model):
    """Расчётный листок сотрудника за месяц (снимок данных на момент расчёта)."""

    period = models.ForeignKey(PayrollPeriod, verbose_name="Ведомость", on_delete=models.CASCADE, related_name="payslips")
    employee = models.ForeignKey("hr.Employee", verbose_name="Сотрудник", on_delete=models.PROTECT, related_name="payslips")
    department = models.ForeignKey("hr.Department", verbose_name="Подразделение", on_delete=models.PROTECT, related_name="+")
    position = models.ForeignKey("hr.Position", verbose_name="Должность", on_delete=models.PROTECT, related_name="+")
    salary = models.DecimalField("Оклад", max_digits=12, decimal_places=2)
    norm_days = models.PositiveSmallIntegerField("Норма, раб. дней")
    worked_days = models.PositiveSmallIntegerField("Отработано, дней")
    vacation_days = models.PositiveSmallIntegerField("Отпуск, календ. дней", default=0)
    sick_days = models.PositiveSmallIntegerField("Больничный, раб. дней", default=0)
    unpaid_days = models.PositiveSmallIntegerField("Без содержания, дней", default=0)
    salary_accrued = models.DecimalField("Оклад за отработанное", max_digits=12, decimal_places=2, default=0)
    vacation_pay = models.DecimalField("Отпускные", max_digits=12, decimal_places=2, default=0)
    sick_pay = models.DecimalField("Больничные", max_digits=12, decimal_places=2, default=0)
    bonus = models.DecimalField("Премия", max_digits=12, decimal_places=2, default=0)
    gross = models.DecimalField("Начислено", max_digits=12, decimal_places=2, default=0)
    withheld = models.DecimalField("Удержано", max_digits=12, decimal_places=2, default=0)
    net = models.DecimalField("К выплате", max_digits=12, decimal_places=2, default=0)
    employer_total = models.DecimalField("Взносы работодателя", max_digits=12, decimal_places=2, default=0)

    class Meta:
        verbose_name = "Расчётный листок"
        verbose_name_plural = "Расчётные листки"
        ordering = ["department__name", "employee__last_name"]
        constraints = [
            models.UniqueConstraint(fields=["period", "employee"], name="unique_payslip"),
            models.CheckConstraint(condition=Q(bonus__gte=0), name="payslip_bonus_nonnegative"),
        ]


class PayslipLine(models.Model):
    """Удержание или взнос в расчётном листке."""

    payslip = models.ForeignKey(Payslip, verbose_name="Листок", on_delete=models.CASCADE, related_name="lines")
    rate = models.ForeignKey(PayrollRate, verbose_name="Ставка", on_delete=models.PROTECT, related_name="+")
    payer = models.CharField("Кто платит", max_length=10, choices=PayrollRate.Payer.choices)
    base = models.DecimalField("База", max_digits=12, decimal_places=2)
    percent = models.DecimalField("Ставка, %", max_digits=5, decimal_places=2)
    amount = models.DecimalField("Сумма", max_digits=12, decimal_places=2)

    class Meta:
        verbose_name = "Строка расчётного листка"
        verbose_name_plural = "Строки расчётного листка"
