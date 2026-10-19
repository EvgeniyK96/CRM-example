from django.conf import settings
from django.db import models

from core.numbering import assign_number


class Department(models.Model):
    """Подразделение: производственный цех или административный отдел."""

    name = models.CharField("Название", max_length=120, unique=True)
    is_production = models.BooleanField("Производственный цех", default=False)
    is_active = models.BooleanField("Действует", default=True)

    class Meta:
        verbose_name = "Подразделение"
        verbose_name_plural = "Подразделения"
        ordering = ["name"]

    def __str__(self):
        return self.name


class Position(models.Model):
    name = models.CharField("Название", max_length=120, unique=True)
    base_salary = models.DecimalField("Базовый оклад", max_digits=12, decimal_places=2, default=0)

    class Meta:
        verbose_name = "Должность"
        verbose_name_plural = "Должности"
        ordering = ["name"]

    def __str__(self):
        return self.name


class Employee(models.Model):
    class Status(models.TextChoices):
        ACTIVE = "active", "Работает"
        LEAVE = "leave", "В отпуске"
        FIRED = "fired", "Уволен"

    user = models.OneToOneField(
        settings.AUTH_USER_MODEL, verbose_name="Учётная запись", null=True, blank=True,
        on_delete=models.SET_NULL, related_name="employee",
    )
    last_name = models.CharField("Фамилия", max_length=80)
    first_name = models.CharField("Имя", max_length=80)
    middle_name = models.CharField("Отчество", max_length=80, blank=True)
    birth_date = models.DateField("Дата рождения", null=True, blank=True)
    tax_id = models.CharField("ИИН/ИНН", max_length=20, blank=True)
    phone = models.CharField("Телефон", max_length=30, blank=True)
    address = models.CharField("Адрес", max_length=255, blank=True)
    department = models.ForeignKey(Department, verbose_name="Подразделение", on_delete=models.PROTECT, related_name="employees")
    position = models.ForeignKey(Position, verbose_name="Должность", on_delete=models.PROTECT, related_name="employees")
    hire_date = models.DateField("Дата приёма")
    fire_date = models.DateField("Дата увольнения", null=True, blank=True)
    status = models.CharField("Статус", max_length=10, choices=Status.choices, default=Status.ACTIVE)
    salary = models.DecimalField("Оклад", max_digits=12, decimal_places=2, default=0,
                                 help_text="Пусто — базовый оклад должности")

    class Meta:
        verbose_name = "Сотрудник"
        verbose_name_plural = "Сотрудники"
        ordering = ["last_name", "first_name"]

    @property
    def full_name(self):
        return " ".join(p for p in (self.last_name, self.first_name, self.middle_name) if p)

    def __str__(self):
        return self.full_name

    def save(self, *args, **kwargs):
        # Оклад по умолчанию — из штатного расписания (базовый оклад должности)
        if not self.salary and self.position_id:
            self.salary = self.position.base_salary
        super().save(*args, **kwargs)


class HROrder(models.Model):
    """Кадровый приказ. Отдел, должность, оклад и увольнение меняются только приказами — так сохраняется история."""

    class Kind(models.TextChoices):
        HIRE = "hire", "Приём на работу"
        TRANSFER = "transfer", "Перевод"
        SALARY = "salary", "Изменение оклада"
        DISMISSAL = "dismissal", "Увольнение"

    number = models.CharField("Номер", max_length=20, unique=True, null=True, blank=True, editable=False)
    kind = models.CharField("Вид приказа", max_length=10, choices=Kind.choices)
    employee = models.ForeignKey(Employee, verbose_name="Сотрудник", on_delete=models.PROTECT, related_name="orders")
    date = models.DateField("Дата вступления в силу")
    # Значения «было → стало» для истории
    from_department = models.ForeignKey(Department, verbose_name="Из подразделения", null=True, blank=True,
                                        on_delete=models.PROTECT, related_name="+")
    to_department = models.ForeignKey(Department, verbose_name="В подразделение", null=True, blank=True,
                                      on_delete=models.PROTECT, related_name="+")
    from_position = models.ForeignKey(Position, verbose_name="С должности", null=True, blank=True,
                                      on_delete=models.PROTECT, related_name="+")
    to_position = models.ForeignKey(Position, verbose_name="На должность", null=True, blank=True,
                                    on_delete=models.PROTECT, related_name="+")
    from_salary = models.DecimalField("Прежний оклад", max_digits=12, decimal_places=2, null=True, blank=True)
    to_salary = models.DecimalField("Новый оклад", max_digits=12, decimal_places=2, null=True, blank=True)
    reason = models.CharField("Основание", max_length=255, blank=True)
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, verbose_name="Автор", null=True, blank=True,
                                   on_delete=models.SET_NULL, related_name="+")
    created_at = models.DateTimeField("Создан", auto_now_add=True)

    class Meta:
        verbose_name = "Кадровый приказ"
        verbose_name_plural = "Кадровые приказы"
        ordering = ["-date", "-pk"]

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        assign_number(self, "ПК")

    def __str__(self):
        return self.number or "Приказ"


class Absence(models.Model):
    """Отсутствие сотрудника: отпуск, больничный, командировка, отпуск без содержания."""

    class Kind(models.TextChoices):
        VACATION = "vacation", "Ежегодный отпуск"
        SICK = "sick", "Больничный"
        BUSINESS_TRIP = "business_trip", "Командировка"
        UNPAID = "unpaid", "Отпуск без содержания"

    employee = models.ForeignKey(Employee, verbose_name="Сотрудник", on_delete=models.CASCADE, related_name="absences")
    kind = models.CharField("Вид", max_length=15, choices=Kind.choices)
    date_from = models.DateField("С")
    date_to = models.DateField("По")
    comment = models.CharField("Комментарий", max_length=255, blank=True)
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, verbose_name="Автор", null=True, blank=True,
                                   on_delete=models.SET_NULL, related_name="+")

    class Meta:
        verbose_name = "Отсутствие"
        verbose_name_plural = "Отсутствия"
        ordering = ["-date_from"]
        constraints = [
            models.CheckConstraint(condition=models.Q(date_to__gte=models.F("date_from")), name="absence_dates_order"),
        ]

    def __str__(self):
        return f"{self.employee}: {self.get_kind_display()} {self.date_from}–{self.date_to}"


class Holiday(models.Model):
    """Праздничный (нерабочий) день производственного календаря."""

    date = models.DateField("Дата", unique=True)
    name = models.CharField("Название", max_length=120)

    class Meta:
        verbose_name = "Праздничный день"
        verbose_name_plural = "Производственный календарь"
        ordering = ["date"]

    def __str__(self):
        return f"{self.date} {self.name}"


class WorkDay(models.Model):
    """
    Рабочий день пользователя (кнопка «Начать день» в шапке). Время — сумма интервалов работы;
    пауза — промежуток между интервалами. Незакрытый день закрывается сам при начале следующего.
    """

    user = models.ForeignKey(settings.AUTH_USER_MODEL, verbose_name="Пользователь", on_delete=models.CASCADE,
                             related_name="workdays")
    date = models.DateField("Дата")
    finished_at = models.DateTimeField("Завершён", null=True, blank=True)
    auto_closed = models.BooleanField("Закрыт автоматически", default=False,
                                      help_text="Сотрудник забыл завершить день — закрыт при начале следующего")
    report = models.TextField("Отчёт за день", blank=True)

    class Meta:
        verbose_name = "Рабочий день"
        verbose_name_plural = "Учёт рабочего времени"
        ordering = ["-date", "user"]
        constraints = [models.UniqueConstraint(fields=["user", "date"], name="workday_once_per_date")]

    def __str__(self):
        return f"{self.user} {self.date}"


class WorkInterval(models.Model):
    day = models.ForeignKey(WorkDay, verbose_name="День", on_delete=models.CASCADE, related_name="intervals")
    started_at = models.DateTimeField("Начало")
    ended_at = models.DateTimeField("Конец", null=True, blank=True)

    class Meta:
        verbose_name = "Интервал работы"
        verbose_name_plural = "Интервалы работы"
        ordering = ["started_at"]
