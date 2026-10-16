from datetime import timedelta
from decimal import Decimal

from django.core.management import call_command
from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils import timezone

from apps.catalog.models import Item, ItemKind, Supplier
from apps.purchasing import services
from apps.purchasing.models import PurchaseOrder, PurchaseOrderLine, Receipt, ReceiptLine

# Закупочные цены за единицу сырья
PRICES = {
    "RAW-001": 350, "RAW-002": 600, "RAW-003": 450, "RAW-004": 2500, "RAW-005": 700, "RAW-006": 4500,
    "RAW-007": 450, "RAW-008": 2200, "RAW-009": 1500, "RAW-010": 1800, "RAW-011": 1200, "RAW-012": 900,
    "RAW-013": 60, "RAW-014": 4000, "RAW-015": 30000, "RAW-016": 5000, "RAW-017": 6000, "RAW-018": 1500,
    "RAW-019": 400, "RAW-020": 150, "RAW-021": 1200, "RAW-022": 3500, "RAW-023": 5500, "RAW-024": 1300,
    "RAW-025": 1600,
}

SUPPLIER_BY_CATEGORY = {
    "Мука и крахмал": "ТОО «Северный мелькомбинат»",
    "Молочное сырьё и жиры": "ТОО «Молочная долина»",
    "Сахар и подсластители": "ТОО «Сахарторг»",
    "Яйцо": "ИП «Птицефабрика Заречная»",
    "Добавки и пряности": "ТОО «Пряности и добавки»",
    "Начинки и декор": "ТОО «Пряности и добавки»",
}


class Command(BaseCommand):
    help = "Начальные остатки сырья (через проведённые приёмки) и отправленная заявка поставщику"

    @transaction.atomic
    def handle(self, *args, **options):
        call_command("seed_catalog", stdout=self.stdout)
        if Receipt.objects.exists():
            self.stdout.write("Приёмки уже есть — пропускаю")
            return

        today = timezone.localdate()
        raw = list(Item.objects.filter(kind=ItemKind.RAW).select_related("category"))
        by_supplier: dict[Supplier, list[Item]] = {}
        for item in raw:
            supplier = Supplier.objects.get(name=SUPPLIER_BY_CATEGORY[item.category.name])
            by_supplier.setdefault(supplier, []).append(item)

        # Две поставки от каждого поставщика: старая (20 дней назад) и свежая (3 дня назад).
        # Партии со сроком годности короче 20 дней в старой поставке окажутся просроченными.
        for days_ago, share in ((20, Decimal("0.4")), (3, Decimal("1.6"))):
            for supplier, items in by_supplier.items():
                receipt = Receipt.objects.create(
                    supplier=supplier, date=today - timedelta(days=days_ago), invoice_number=f"НК-{days_ago}-{supplier.pk}"
                )
                ReceiptLine.objects.bulk_create(
                    ReceiptLine(receipt=receipt, item=item, quantity=max((item.min_stock * share).quantize(Decimal(1)), Decimal(1)),
                                price=PRICES[item.code])
                    for item in items
                )
                services.post_receipt(receipt)

        # Отправленная заявка на муку и сахар — её можно принять в интерфейсе
        order = PurchaseOrder.objects.create(
            supplier=Supplier.objects.get(name="ТОО «Северный мелькомбинат»"),
            expected_date=today + timedelta(days=2), comment="Пополнение запаса муки",
        )
        PurchaseOrderLine.objects.create(order=order, item=Item.objects.get(code="RAW-001"), quantity=500, price=340)
        PurchaseOrderLine.objects.create(order=order, item=Item.objects.get(code="RAW-002"), quantity=50, price=600)
        services.send(order)
        self.stdout.write(self.style.SUCCESS("Остатки сырья и заявка поставщику созданы"))
