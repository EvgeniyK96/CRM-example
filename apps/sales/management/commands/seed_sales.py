from datetime import timedelta
from decimal import Decimal

from django.core.management import call_command
from django.core.management.base import BaseCommand
from django.db import transaction
from django.db.models import Avg
from django.utils import timezone

from apps.accounts.models import User
from apps.catalog.models import Item
from apps.recipes.models import Recipe
from apps.recipes.services import calculate
from apps.sales import services
from apps.sales.models import Client, SalesOrder, SalesOrderLine
from apps.warehouse import services as stock
from apps.warehouse.models import Lot

# название, тип, скидка %, отсрочка дней, адрес доставки
CLIENTS = [
    ("ТОО «Оптовик-Север»", "wholesale", 10, 14, "г. Алматы, ул. Складская, 12"),
    ("ТОО «Торговый дом Восток»", "wholesale", 7, 21, "г. Алматы, мкр. Восток, 3"),
    ("Магазин «Колосок»", "store", 3, 7, "г. Алматы, ул. Пекарная, 5"),
    ("ИП Ахметова, магазин «У дома»", "store", 0, 0, "г. Алматы, ул. Садовая, 18"),
    ("Кофейня «Корица»", "store", 5, 7, "г. Алматы, пр. Кофейный, 1"),
    ("Фирменный магазин №1 (пр. Абая)", "brand_store", 0, 0, "г. Алматы, пр. Абая, 40"),
    ("Фирменный магазин №2 (мкр. Самал)", "brand_store", 0, 0, "г. Алматы, мкр. Самал-2, 7"),
]

# Начальные остатки готовой продукции: артикул → (количество, сколько дней назад произведено)
OPENING_STOCK = {"PRD-001": (5, 1), "PRD-004": (150, 5), "PRD-005": (80, 10), "PRD-006": (300, 20),
                 "PRD-007": (20, 15), "PRD-008": (40, 0)}

# клиент, через сколько дней отгрузка, [(артикул, количество)], подтверждать ли
ORDERS = [
    ("ТОО «Оптовик-Север»", 3, [("PRD-004", 100), ("PRD-006", 200)], True),
    ("ТОО «Торговый дом Восток»", 5, [("PRD-004", 120), ("PRD-007", 30)], True),
    ("Фирменный магазин №1 (пр. Абая)", 1, [("PRD-001", 10), ("PRD-003", 50), ("PRD-008", 30)], True),
    ("Магазин «Колосок»", 2, [("PRD-009", 50), ("PRD-002", 3)], False),
]


def recipe_unit_cost(product: Item) -> Decimal:
    """Себестоимость единицы продукции по активной рецептуре и средней цене партий сырья."""
    recipe = Recipe.objects.get(product=product, status=Recipe.Status.ACTIVE)
    total = Decimal(0)
    for line in calculate(recipe, Decimal(1)):
        avg = Lot.objects.filter(item_id=line["ingredient"]).aggregate(a=Avg("unit_cost"))["a"] or 0
        total += line["quantity"] * Decimal(avg)
    return total.quantize(Decimal("0.01"))


class Command(BaseCommand):
    help = "Клиенты, начальные остатки готовой продукции и заказы в разных статусах"

    @transaction.atomic
    def handle(self, *args, **options):
        call_command("seed_recipes", stdout=self.stdout)
        call_command("seed_purchasing", stdout=self.stdout)
        if Client.objects.exists():
            self.stdout.write("Клиенты уже есть — пропускаю")
            return

        today = timezone.localdate()
        for name, kind, discount, delay, address in CLIENTS:
            Client.objects.create(name=name, kind=kind, discount_percent=discount, payment_delay_days=delay,
                                  delivery_address=address)

        products = {i.code: i for i in Item.objects.filter(kind="product")}
        for code, (qty, days_ago) in OPENING_STOCK.items():
            product = products[code]
            stock.enter_opening_balance(product, Decimal(qty), on_date=today - timedelta(days=days_ago),
                                        unit_cost=recipe_unit_cost(product))

        manager = User.objects.filter(role="sales").first()
        for client_name, days, lines, do_confirm in ORDERS:
            client = Client.objects.get(name=client_name)
            order = SalesOrder.objects.create(
                client=client, delivery_date=today + timedelta(days=days), discount_percent=client.discount_percent,
                delivery_address=client.delivery_address, created_by=manager,
            )
            SalesOrderLine.objects.bulk_create(
                SalesOrderLine(order=order, item=products[code], quantity=qty,
                               price=services.list_price(products[code], order.discount_percent))
                for code, qty in lines
            )
            if do_confirm:
                services.confirm(order, manager)
        self.stdout.write(self.style.SUCCESS("Клиенты, остатки продукции и заказы созданы"))
