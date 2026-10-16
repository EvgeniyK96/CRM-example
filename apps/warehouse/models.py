from decimal import Decimal

from django.conf import settings
from django.db import models
from django.db.models import DecimalField, Q, Sum, Value
from django.db.models.functions import Coalesce
from django.utils import timezone

from core.numbering import assign_number

QTY_FIELD = DecimalField(max_digits=14, decimal_places=3)


def balance_expr(path="moves__quantity"):
    """Остаток = сумма движений (0, если движений нет)."""
    return Coalesce(Sum(path), Value(Decimal(0)), output_field=QTY_FIELD)


class LotQuerySet(models.QuerySet):
    def with_balance(self):
        return self.annotate(balance=balance_expr())

    def usable(self, on_date=None):
        """Непросроченные партии с положительным остатком, в порядке FEFO."""
        on_date = on_date or timezone.localdate()
        return (
            self.filter(expiry_date__gte=on_date)
            .with_balance()
            .filter(balance__gt=0)
            .order_by("expiry_date", "pk")
        )


class Lot(models.Model):
    """Партия сырья или готовой продукции. Остаток партии хранится не здесь, а считается из движений."""

    number = models.CharField("Номер", max_length=20, unique=True, null=True, blank=True, editable=False)
    item = models.ForeignKey("catalog.Item", verbose_name="Номенклатура", on_delete=models.PROTECT, related_name="lots")
    supplier = models.ForeignKey(
        "catalog.Supplier", verbose_name="Поставщик", null=True, blank=True, on_delete=models.PROTECT,
        related_name="lots",
    )
    date = models.DateField("Дата поступления / производства")
    expiry_date = models.DateField("Годен до")
    unit_cost = models.DecimalField("Себестоимость единицы", max_digits=12, decimal_places=2, default=0)
    created_at = models.DateTimeField("Создана", auto_now_add=True)

    objects = LotQuerySet.as_manager()

    class Meta:
        verbose_name = "Партия"
        verbose_name_plural = "Партии"
        ordering = ["expiry_date", "pk"]
        constraints = [models.CheckConstraint(condition=Q(expiry_date__gte=models.F("date")), name="lot_expiry_after_date")]

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        assign_number(self, "П", width=6)

    def __str__(self):
        return f"{self.number} {self.item.name}"


class MoveKind(models.TextChoices):
    RECEIPT = "receipt", "Приход от поставщика"
    PRODUCTION_OUT = "production_out", "Списание в производство"
    PRODUCTION_IN = "production_in", "Выпуск продукции"
    SHIPMENT = "shipment", "Отгрузка клиенту"
    WRITE_OFF = "write_off", "Списание (брак, порча)"
    ADJUSTMENT = "adjustment", "Корректировка"


class StockMove(models.Model):
    """Движение по партии: плюс — приход, минус — расход. Записи не редактируются."""

    lot = models.ForeignKey(Lot, verbose_name="Партия", on_delete=models.PROTECT, related_name="moves")
    kind = models.CharField("Вид движения", max_length=20, choices=MoveKind.choices)
    quantity = models.DecimalField("Количество", max_digits=12, decimal_places=3)
    reference = models.CharField("Основание", max_length=200, blank=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, verbose_name="Кто провёл", null=True, blank=True, on_delete=models.SET_NULL,
        related_name="+",
    )
    created_at = models.DateTimeField("Дата и время", auto_now_add=True, db_index=True)

    class Meta:
        verbose_name = "Движение"
        verbose_name_plural = "Движения"
        ordering = ["-created_at", "-pk"]
        constraints = [models.CheckConstraint(condition=~Q(quantity=0), name="move_quantity_nonzero")]

    def __str__(self):
        return f"{self.get_kind_display()} {self.quantity} ({self.lot})"
