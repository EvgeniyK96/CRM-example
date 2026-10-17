from django.conf import settings
from django.db import models
from django.db.models import Q

from core.numbering import assign_number


class ProductionTask(models.Model):
    """Производственное задание цеху: выпустить продукт по зафиксированной версии рецептуры."""

    class Status(models.TextChoices):
        PLANNED = "planned", "Запланировано"
        IN_PROGRESS = "in_progress", "В работе"
        DONE = "done", "Выполнено"
        CANCELLED = "cancelled", "Отменено"

    OPEN_STATUSES = (Status.PLANNED, Status.IN_PROGRESS)

    number = models.CharField("Номер", max_length=20, unique=True, null=True, blank=True, editable=False)
    department = models.ForeignKey(
        "hr.Department", verbose_name="Цех", on_delete=models.PROTECT, related_name="production_tasks"
    )
    product = models.ForeignKey("catalog.Item", verbose_name="Продукт", on_delete=models.PROTECT, related_name="+")
    recipe = models.ForeignKey("recipes.Recipe", verbose_name="Рецептура", on_delete=models.PROTECT, related_name="tasks")
    planned_qty = models.DecimalField("План", max_digits=12, decimal_places=3)
    planned_date = models.DateField("Плановая дата")
    status = models.CharField("Статус", max_length=12, choices=Status.choices, default=Status.PLANNED)
    actual_qty = models.DecimalField("Выпущено годной", max_digits=12, decimal_places=3, null=True, blank=True)
    defect_qty = models.DecimalField("Брак", max_digits=12, decimal_places=3, default=0)
    raw_cost = models.DecimalField("Стоимость списанного сырья", max_digits=14, decimal_places=2, null=True, blank=True)
    output_lot = models.OneToOneField(
        "warehouse.Lot", verbose_name="Выпущенная партия", null=True, blank=True, on_delete=models.PROTECT,
        related_name="production_task",
    )
    comment = models.TextField("Комментарий", blank=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, verbose_name="Создал", null=True, blank=True, on_delete=models.SET_NULL, related_name="+"
    )
    created_at = models.DateTimeField("Создано", auto_now_add=True)
    started_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, verbose_name="Запустил", null=True, blank=True, on_delete=models.SET_NULL, related_name="+"
    )
    started_at = models.DateTimeField("Запущено", null=True, blank=True)
    finished_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, verbose_name="Завершил", null=True, blank=True, on_delete=models.SET_NULL, related_name="+"
    )
    finished_at = models.DateTimeField("Завершено", null=True, blank=True)

    class Meta:
        verbose_name = "Производственное задание"
        verbose_name_plural = "Производственные задания"
        ordering = ["planned_date", "pk"]
        constraints = [
            models.CheckConstraint(condition=Q(planned_qty__gt=0), name="task_planned_positive"),
            models.CheckConstraint(condition=Q(defect_qty__gte=0), name="task_defect_nonnegative"),
        ]

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        assign_number(self, "ПЗ")

    def __str__(self):
        return self.number or "Задание"

    @property
    def is_editable(self):
        return self.status == self.Status.PLANNED


class TaskAllocation(models.Model):
    """Какая часть задания предназначена строке заказа клиента."""

    task = models.ForeignKey(ProductionTask, verbose_name="Задание", on_delete=models.CASCADE, related_name="allocations")
    order_line = models.ForeignKey(
        "sales.SalesOrderLine", verbose_name="Строка заказа", on_delete=models.CASCADE, related_name="allocations"
    )
    quantity = models.DecimalField("Количество", max_digits=12, decimal_places=3)
    fulfilled = models.DecimalField("Выполнено", max_digits=12, decimal_places=3, default=0)

    class Meta:
        verbose_name = "Распределение по заказу"
        verbose_name_plural = "Распределения по заказам"
        constraints = [
            models.UniqueConstraint(fields=["task", "order_line"], name="unique_task_order_line"),
            models.CheckConstraint(condition=Q(quantity__gt=0), name="allocation_qty_positive"),
        ]


class TaskConsumption(models.Model):
    """Списание партии сырья в задание — основа прослеживаемости «продукция ← сырьё»."""

    task = models.ForeignKey(ProductionTask, verbose_name="Задание", on_delete=models.PROTECT, related_name="consumptions")
    move = models.OneToOneField(
        "warehouse.StockMove", verbose_name="Движение", on_delete=models.PROTECT, related_name="consumption"
    )

    class Meta:
        verbose_name = "Списание сырья"
        verbose_name_plural = "Списания сырья"
