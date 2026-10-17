from django.conf import settings
from django.db import models
from django.db.models import Q

from core.numbering import assign_number


class Client(models.Model):
    class Kind(models.TextChoices):
        WHOLESALE = "wholesale", "Оптовый покупатель"
        STORE = "store", "Магазин"
        BRAND_STORE = "brand_store", "Фирменный магазин"

    kind = models.CharField("Тип клиента", max_length=15, choices=Kind.choices)
    name = models.CharField("Название", max_length=200, unique=True)
    tax_id = models.CharField("БИН/ИНН", max_length=20, blank=True)
    contact_person = models.CharField("Контактное лицо", max_length=120, blank=True)
    phone = models.CharField("Телефон", max_length=30, blank=True)
    email = models.EmailField("Email", blank=True)
    legal_address = models.CharField("Юридический адрес", max_length=255, blank=True)
    delivery_address = models.CharField("Адрес доставки", max_length=255, blank=True)
    discount_percent = models.DecimalField("Скидка, %", max_digits=5, decimal_places=2, default=0)
    payment_delay_days = models.PositiveIntegerField("Отсрочка платежа, дней", default=0, help_text="0 — предоплата")
    note = models.TextField("Примечание", blank=True)
    is_active = models.BooleanField("Активен", default=True)

    class Meta:
        verbose_name = "Клиент"
        verbose_name_plural = "Клиенты"
        ordering = ["name"]
        constraints = [
            models.CheckConstraint(condition=Q(discount_percent__gte=0, discount_percent__lt=100), name="client_discount_range"),
        ]

    def __str__(self):
        return self.name


class SalesOrder(models.Model):
    class Status(models.TextChoices):
        NEW = "new", "Новый"
        CONFIRMED = "confirmed", "Подтверждён"
        IN_PRODUCTION = "in_production", "В производстве"
        READY = "ready", "Готов к отгрузке"
        SHIPPED = "shipped", "Отгружен"
        CANCELLED = "cancelled", "Отменён"

    # Заказы, которые держат резерв готовой продукции
    OPEN_STATUSES = (Status.CONFIRMED, Status.IN_PRODUCTION, Status.READY)

    number = models.CharField("Номер", max_length=20, unique=True, null=True, blank=True, editable=False)
    client = models.ForeignKey(Client, verbose_name="Клиент", on_delete=models.PROTECT, related_name="orders")
    status = models.CharField("Статус", max_length=15, choices=Status.choices, default=Status.NEW)
    delivery_date = models.DateField("Дата отгрузки")
    delivery_address = models.CharField("Адрес доставки", max_length=255, blank=True)
    discount_percent = models.DecimalField(
        "Скидка, %", max_digits=5, decimal_places=2, default=0, help_text="Фиксируется из карточки клиента при создании"
    )
    comment = models.TextField("Комментарий", blank=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, verbose_name="Менеджер", null=True, blank=True, on_delete=models.SET_NULL,
        related_name="+",
    )
    created_at = models.DateTimeField("Создан", auto_now_add=True)
    confirmed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, verbose_name="Подтвердил", null=True, blank=True, on_delete=models.SET_NULL,
        related_name="+",
    )
    confirmed_at = models.DateTimeField("Подтверждён", null=True, blank=True)

    class Meta:
        verbose_name = "Заказ клиента"
        verbose_name_plural = "Заказы клиентов"
        ordering = ["-created_at"]
        constraints = [
            models.CheckConstraint(condition=Q(discount_percent__gte=0, discount_percent__lt=100), name="order_discount_range"),
        ]

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        assign_number(self, "ЗК")

    def __str__(self):
        return self.number or "Заказ"

    @property
    def is_editable(self):
        return self.status == self.Status.NEW


class SalesOrderLine(models.Model):
    order = models.ForeignKey(SalesOrder, verbose_name="Заказ", on_delete=models.CASCADE, related_name="lines")
    item = models.ForeignKey(
        "catalog.Item", verbose_name="Продукция", on_delete=models.PROTECT, related_name="+",
        limit_choices_to={"kind": "product"},
    )
    quantity = models.DecimalField("Количество", max_digits=12, decimal_places=3)
    price = models.DecimalField("Цена со скидкой", max_digits=12, decimal_places=2)
    # Заполняются при подтверждении заказа
    reserved_qty = models.DecimalField("Зарезервировано со склада", max_digits=12, decimal_places=3, default=0)
    to_produce = models.DecimalField("Требуется произвести", max_digits=12, decimal_places=3, default=0)

    class Meta:
        verbose_name = "Строка заказа"
        verbose_name_plural = "Строки заказа"
        constraints = [
            models.UniqueConstraint(fields=["order", "item"], name="unique_item_in_sales_order"),
            models.CheckConstraint(condition=Q(quantity__gt=0), name="sales_line_qty_positive"),
            models.CheckConstraint(condition=Q(price__gte=0), name="sales_line_price_nonnegative"),
            models.CheckConstraint(
                condition=Q(reserved_qty__gte=0, to_produce__gte=0), name="sales_line_split_nonnegative"
            ),
        ]

    @property
    def amount(self):
        return self.quantity * self.price


class Shipment(models.Model):
    """Отгрузка заказа клиенту (расходная накладная). Создаётся сразу проведённой."""

    number = models.CharField("Номер", max_length=20, unique=True, null=True, blank=True, editable=False)
    order = models.OneToOneField(SalesOrder, verbose_name="Заказ", on_delete=models.PROTECT, related_name="shipment")
    date = models.DateField("Дата отгрузки")
    vehicle = models.CharField("Транспорт", max_length=100, blank=True)
    driver = models.CharField("Водитель", max_length=120, blank=True)
    comment = models.TextField("Комментарий", blank=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, verbose_name="Отгрузил", null=True, blank=True, on_delete=models.SET_NULL,
        related_name="+",
    )
    created_at = models.DateTimeField("Создана", auto_now_add=True)

    class Meta:
        verbose_name = "Отгрузка"
        verbose_name_plural = "Отгрузки"
        ordering = ["-date", "-pk"]

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        assign_number(self, "ОТ")

    def __str__(self):
        return self.number or "Отгрузка"


class ShipmentItem(models.Model):
    """Списание конкретной партии под строку заказа — прослеживаемость «партия → клиент»."""

    shipment = models.ForeignKey(Shipment, verbose_name="Отгрузка", on_delete=models.CASCADE, related_name="items")
    order_line = models.ForeignKey(SalesOrderLine, verbose_name="Строка заказа", on_delete=models.PROTECT, related_name="+")
    move = models.OneToOneField(
        "warehouse.StockMove", verbose_name="Движение", on_delete=models.PROTECT, related_name="shipment_item"
    )

    class Meta:
        verbose_name = "Строка отгрузки"
        verbose_name_plural = "Строки отгрузки"
