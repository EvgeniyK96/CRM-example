from django.conf import settings
from django.db import models


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

    class Meta:
        verbose_name = "Сотрудник"
        verbose_name_plural = "Сотрудники"
        ordering = ["last_name", "first_name"]

    @property
    def full_name(self):
        return " ".join(p for p in (self.last_name, self.first_name, self.middle_name) if p)

    def __str__(self):
        return self.full_name
