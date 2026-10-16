from django.conf import settings
from django.db import models
from django.db.models import Q
from django.utils import timezone

from core.numbering import assign_number


class PurchaseOrder(models.Model):
    """Заявка поставщику на сырьё."""

    class Status(models.TextChoices):
        DRAFT = "draft", "Черновик"
        SENT = "sent", "Отправлена"
        PARTIAL = "partial", "Получена частично"
        RECEIVED = "received", "Получена"
        CANCELLED = "cancelled", "Отменена"

    number = models.CharField("Номер", max_length=20, unique=True, null=True, blank=True, editable=False)
    supplier = models.ForeignKey(
        "catalog.Supplier", verbose_name="Поставщик", on_delete=models.PROTECT, related_name="purchase_orders"
    )
    status = models.CharField("Статус", max_length=10, choices=Status.choices, default=Status.DRAFT)
    expected_date = models.DateField("Ожидаемая дата поставки", null=True, blank=True)
    comment = models.TextField("Комментарий", blank=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, verbose_name="Автор", null=True, blank=True, on_delete=models.SET_NULL,
        related_name="+",
    )
    created_at = models.DateTimeField("Создана", auto_now_add=True)

    class Meta:
        verbose_name = "Заявка поставщику"
        verbose_name_plural = "Заявки поставщикам"
        ordering = ["-created_at"]

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        assign_number(self, "ЗП")

    def __str__(self):
        return self.number or "Заявка"

    @property
    def is_editable(self):
        return self.status == self.Status.DRAFT


class PurchaseOrderLine(models.Model):
    order = models.ForeignKey(PurchaseOrder, verbose_name="Заявка", on_delete=models.CASCADE, related_name="lines")
    item = models.ForeignKey(
        "catalog.Item", verbose_name="Сырьё", on_delete=models.PROTECT, related_name="+",
        limit_choices_to={"kind": "raw"},
    )
    quantity = models.DecimalField("Количество", max_digits=12, decimal_places=3)
    price = models.DecimalField("Цена за единицу", max_digits=12, decimal_places=2, default=0)

    class Meta:
        verbose_name = "Строка заявки"
        verbose_name_plural = "Строки заявки"
        constraints = [
            models.UniqueConstraint(fields=["order", "item"], name="unique_item_in_purchase_order"),
            models.CheckConstraint(condition=Q(quantity__gt=0), name="po_line_qty_positive"),
            models.CheckConstraint(condition=Q(price__gte=0), name="po_line_price_nonnegative"),
        ]


class Receipt(models.Model):
    """Приёмка сырья (приходная накладная). При проведении создаёт партии на складе."""

    class Status(models.TextChoices):
        DRAFT = "draft", "Черновик"
        POSTED = "posted", "Проведена"

    number = models.CharField("Номер", max_length=20, unique=True, null=True, blank=True, editable=False)
    supplier = models.ForeignKey(
        "catalog.Supplier", verbose_name="Поставщик", on_delete=models.PROTECT, related_name="receipts"
    )
    order = models.ForeignKey(
        PurchaseOrder, verbose_name="По заявке", null=True, blank=True, on_delete=models.PROTECT,
        related_name="receipts",
    )
    date = models.DateField("Дата приёмки", default=timezone.localdate)
    invoice_number = models.CharField("Номер накладной поставщика", max_length=50, blank=True)
    status = models.CharField("Статус", max_length=10, choices=Status.choices, default=Status.DRAFT)
    comment = models.TextField("Комментарий", blank=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, verbose_name="Автор", null=True, blank=True, on_delete=models.SET_NULL,
        related_name="+",
    )
    created_at = models.DateTimeField("Создана", auto_now_add=True)
    posted_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, verbose_name="Провёл", null=True, blank=True, on_delete=models.SET_NULL,
        related_name="+",
    )
    posted_at = models.DateTimeField("Проведена", null=True, blank=True)

    class Meta:
        verbose_name = "Приёмка"
        verbose_name_plural = "Приёмки"
        ordering = ["-date", "-pk"]

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        assign_number(self, "ПР")

    def __str__(self):
        return self.number or "Приёмка"

    @property
    def is_editable(self):
        return self.status == self.Status.DRAFT


class ReceiptLine(models.Model):
    receipt = models.ForeignKey(Receipt, verbose_name="Приёмка", on_delete=models.CASCADE, related_name="lines")
    item = models.ForeignKey(
        "catalog.Item", verbose_name="Сырьё", on_delete=models.PROTECT, related_name="+",
        limit_choices_to={"kind": "raw"},
    )
    quantity = models.DecimalField("Количество", max_digits=12, decimal_places=3)
    price = models.DecimalField("Цена за единицу", max_digits=12, decimal_places=2, default=0)
    expiry_date = models.DateField("Годен до", null=True, blank=True, help_text="Пусто — по сроку годности товара")
    order_line = models.ForeignKey(
        PurchaseOrderLine, verbose_name="Строка заявки", null=True, blank=True, on_delete=models.PROTECT,
        related_name="receipt_lines",
    )
    lot = models.OneToOneField(
        "warehouse.Lot", verbose_name="Созданная партия", null=True, blank=True, on_delete=models.PROTECT,
        related_name="receipt_line",
    )

    class Meta:
        verbose_name = "Строка приёмки"
        verbose_name_plural = "Строки приёмки"
        constraints = [
            models.CheckConstraint(condition=Q(quantity__gt=0), name="receipt_line_qty_positive"),
            models.CheckConstraint(condition=Q(price__gte=0), name="receipt_line_price_nonnegative"),
        ]
