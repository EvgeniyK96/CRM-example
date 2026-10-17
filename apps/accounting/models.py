from django.conf import settings
from django.db import models
from django.db.models import Q

from core.numbering import assign_number


class Account(models.Model):
    """Счёт бухгалтерского учёта (упрощённый план счетов по образцу типового плана РК)."""

    class Type(models.TextChoices):
        ASSET = "asset", "Активы"
        LIABILITY = "liability", "Обязательства"
        EQUITY = "equity", "Капитал"
        INCOME = "income", "Доходы"
        EXPENSE = "expense", "Расходы"

    # Типы с нормальным дебетовым сальдо; у остальных нормальное сальдо кредитовое
    DEBIT_NATURE = (Type.ASSET, Type.EXPENSE)

    code = models.CharField("Код", max_length=10, unique=True)
    name = models.CharField("Название", max_length=200)
    type = models.CharField("Тип", max_length=10, choices=Type.choices)
    is_active = models.BooleanField("Используется", default=True)

    class Meta:
        verbose_name = "Счёт"
        verbose_name_plural = "План счетов"
        ordering = ["code"]

    def __str__(self):
        return f"{self.code} {self.name}"


class JournalEntry(models.Model):
    """Хозяйственная операция: одна или несколько проводок по одному основанию."""

    class Source(models.TextChoices):
        MANUAL = "manual", "Ручная операция"
        RECEIPT = "receipt", "Приёмка сырья"
        PRODUCTION_START = "production_start", "Запуск производства"
        PRODUCTION_FINISH = "production_finish", "Выпуск продукции"
        SHIPMENT = "shipment", "Отгрузка"
        WRITE_OFF = "write_off", "Списание"
        OPENING = "opening", "Начальные остатки"
        PAYMENT = "payment", "Платёж"

    date = models.DateField("Дата")
    description = models.CharField("Содержание", max_length=255)
    source_type = models.CharField("Основание", max_length=20, choices=Source.choices, default=Source.MANUAL)
    source_id = models.PositiveIntegerField("ID документа", null=True, blank=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, verbose_name="Автор", null=True, blank=True, on_delete=models.SET_NULL, related_name="+"
    )
    created_at = models.DateTimeField("Создана", auto_now_add=True)

    class Meta:
        verbose_name = "Операция"
        verbose_name_plural = "Журнал операций"
        ordering = ["-date", "-pk"]
        # Одно основание — одна операция: автопроводки не задваиваются (в т.ч. при повторном backfill)
        constraints = [
            models.UniqueConstraint(
                fields=["source_type", "source_id"], condition=Q(source_id__isnull=False), name="unique_entry_source"
            ),
        ]

    def __str__(self):
        return f"{self.date} {self.description}"


class Posting(models.Model):
    """Проводка: Дт счёт — Кт счёт — сумма, с аналитикой по контрагенту."""

    entry = models.ForeignKey(JournalEntry, verbose_name="Операция", on_delete=models.CASCADE, related_name="postings")
    debit = models.ForeignKey(Account, verbose_name="Дебет", on_delete=models.PROTECT, related_name="debit_postings")
    credit = models.ForeignKey(Account, verbose_name="Кредит", on_delete=models.PROTECT, related_name="credit_postings")
    amount = models.DecimalField("Сумма", max_digits=14, decimal_places=2)
    client = models.ForeignKey(
        "sales.Client", verbose_name="Клиент", null=True, blank=True, on_delete=models.PROTECT, related_name="+"
    )
    supplier = models.ForeignKey(
        "catalog.Supplier", verbose_name="Поставщик", null=True, blank=True, on_delete=models.PROTECT, related_name="+"
    )
    comment = models.CharField("Комментарий", max_length=255, blank=True)

    class Meta:
        verbose_name = "Проводка"
        verbose_name_plural = "Проводки"
        constraints = [
            models.CheckConstraint(condition=Q(amount__gt=0), name="posting_amount_positive"),
            models.CheckConstraint(condition=~Q(debit=models.F("credit")), name="posting_different_accounts"),
        ]


class Invoice(models.Model):
    """Счёт покупателю — создаётся при отгрузке; срок оплаты по отсрочке клиента."""

    number = models.CharField("Номер", max_length=20, unique=True, null=True, blank=True, editable=False)
    client = models.ForeignKey("sales.Client", verbose_name="Клиент", on_delete=models.PROTECT, related_name="invoices")
    shipment = models.OneToOneField(
        "sales.Shipment", verbose_name="Отгрузка", null=True, blank=True, on_delete=models.PROTECT, related_name="invoice"
    )
    date = models.DateField("Дата")
    due_date = models.DateField("Оплатить до")
    amount = models.DecimalField("Сумма", max_digits=14, decimal_places=2)
    created_at = models.DateTimeField("Создан", auto_now_add=True)

    class Meta:
        verbose_name = "Счёт покупателю"
        verbose_name_plural = "Счета покупателям"
        ordering = ["-date", "-pk"]
        constraints = [models.CheckConstraint(condition=Q(amount__gt=0), name="invoice_amount_positive")]

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        assign_number(self, "СЧ")

    def __str__(self):
        return self.number or "Счёт"


class Payment(models.Model):
    class Direction(models.TextChoices):
        INCOMING = "incoming", "Поступление от клиента"
        OUTGOING = "outgoing", "Оплата поставщику"

    class Method(models.TextChoices):
        BANK = "bank", "Расчётный счёт"
        CASH = "cash", "Касса"

    number = models.CharField("Номер", max_length=20, unique=True, null=True, blank=True, editable=False)
    direction = models.CharField("Направление", max_length=10, choices=Direction.choices)
    method = models.CharField("Способ", max_length=10, choices=Method.choices, default=Method.BANK)
    date = models.DateField("Дата")
    amount = models.DecimalField("Сумма", max_digits=14, decimal_places=2)
    client = models.ForeignKey(
        "sales.Client", verbose_name="Клиент", null=True, blank=True, on_delete=models.PROTECT, related_name="payments"
    )
    supplier = models.ForeignKey(
        "catalog.Supplier", verbose_name="Поставщик", null=True, blank=True, on_delete=models.PROTECT,
        related_name="payments",
    )
    invoice = models.ForeignKey(
        Invoice, verbose_name="В оплату счёта", null=True, blank=True, on_delete=models.PROTECT, related_name="+",
        help_text="Пусто — разнести на самые старые неоплаченные счета клиента",
    )
    comment = models.CharField("Назначение платежа", max_length=255, blank=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, verbose_name="Автор", null=True, blank=True, on_delete=models.SET_NULL, related_name="+"
    )
    created_at = models.DateTimeField("Создан", auto_now_add=True)

    class Meta:
        verbose_name = "Платёж"
        verbose_name_plural = "Платежи"
        ordering = ["-date", "-pk"]
        constraints = [
            models.CheckConstraint(condition=Q(amount__gt=0), name="payment_amount_positive"),
            models.CheckConstraint(
                condition=(Q(direction="incoming", client__isnull=False, supplier__isnull=True)
                           | Q(direction="outgoing", supplier__isnull=False, client__isnull=True)),
                name="payment_counterparty_matches_direction",
            ),
        ]

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        assign_number(self, "ПП")

    def __str__(self):
        return self.number or "Платёж"


class PaymentAllocation(models.Model):
    """Какая часть поступления закрыла какой счёт."""

    payment = models.ForeignKey(Payment, verbose_name="Платёж", on_delete=models.CASCADE, related_name="allocations")
    invoice = models.ForeignKey(Invoice, verbose_name="Счёт", on_delete=models.PROTECT, related_name="allocations")
    amount = models.DecimalField("Сумма", max_digits=14, decimal_places=2)

    class Meta:
        verbose_name = "Разнесение платежа"
        verbose_name_plural = "Разнесение платежей"
        constraints = [models.CheckConstraint(condition=Q(amount__gt=0), name="allocation_amount_positive")]
