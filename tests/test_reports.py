from datetime import timedelta
from decimal import Decimal

import pytest
from django.utils import timezone

from apps.accounts.models import Role
from apps.catalog.models import Item, ItemKind, Unit
from apps.hr.models import Department
from apps.production import services as production
from apps.recipes.models import Recipe, RecipeLine
from apps.recipes.services import activate
from apps.sales import services as sales
from apps.sales.models import Client, SalesOrder, SalesOrderLine
from apps.warehouse import services as stock

D = Decimal
TODAY = timezone.localdate()
DASHBOARD = "/api/reports/dashboard/"


@pytest.fixture
def world(db):
    """Мука (мин. остаток 50) и пряник с рецептурой; 5 кг муки по 300."""
    kg = Unit.objects.create(code="кг", name="килограмм")
    pcs = Unit.objects.create(code="шт", name="штука", is_fractional=False)
    shop = Department.objects.create(name="Пряничный цех", is_production=True)
    flour = Item.objects.create(kind=ItemKind.RAW, code="R1", name="Мука", unit=kg, shelf_life_days=100, min_stock=50)
    ginger = Item.objects.create(kind=ItemKind.PRODUCT, code="P1", name="Пряник", unit=pcs, shelf_life_days=30,
                                 department=shop, sale_price=100)
    recipe = Recipe.objects.create(product=ginger, version=1, output_qty=10)
    RecipeLine.objects.create(recipe=recipe, ingredient=flour, quantity=1)
    activate(recipe)
    stock.receive(flour, D(5), on_date=TODAY, unit_cost=D(300))
    return {"flour": flour, "ginger": ginger, "shop": shop}


def make_and_ship(world, qty=20, defect=0):
    task = production.create_task(world["ginger"], D(qty), TODAY)
    production.start(task)
    production.finish(task, D(qty - defect), D(defect))
    client = Client.objects.get_or_create(name="Магазин", defaults={"kind": "store"})[0]
    order = SalesOrder.objects.create(client=client, delivery_date=TODAY)
    SalesOrderLine.objects.create(order=order, item=world["ginger"], quantity=10, price=100)
    sales.ship(sales.confirm(order))


def test_dashboard_sections_by_role(make_client, world):
    expected = {
        Role.ADMIN: ["sales", "finance", "production", "warehouse"],
        Role.STOREKEEPER: ["warehouse"],
        Role.SALES: ["sales", "finance"],
        Role.SHOP_HEAD: ["production", "warehouse"],
        Role.HR: [],
    }
    for role, sections in expected.items():
        data = make_client(role).get(DASHBOARD).data
        assert data["sections"] == sections, role
        assert ("sales" in data) == ("sales" in sections)  # чужие разделы не отдаются вовсе


def test_sales_numbers(make_client, world):
    make_and_ship(world, qty=20)  # 2 кг муки → себестоимость пряника 30
    data = make_client(Role.ACCOUNTANT).get(DASHBOARD).data["sales"]
    assert (data["revenue"], data["gross_profit"]) == (D(1000), D(700))
    assert data["by_day"][-1] == {"date": TODAY, "revenue": D(1000)}
    assert len(data["by_day"]) == TODAY.day  # каждый день периода, включая дни без продаж
    top = data["top_products"][0]
    assert (top["name"], top["quantity"], top["margin_percent"]) == ("Пряник", 10, D("70.0"))
    assert data["orders"]["shipped"] == 1


def test_previous_period_comparison(make_client, world):
    make_and_ship(world)
    start = TODAY + timedelta(days=1)
    data = make_client(Role.SALES).get(f"{DASHBOARD}?date_from={start}&date_to={start + timedelta(days=6)}").data
    assert data["sales"]["revenue"] == 0 and data["sales"]["revenue_prev"] == 1000


def test_production_load_and_defects(make_client, world):
    make_and_ship(world, qty=20, defect=4)
    production.create_task(world["ginger"], D(5), TODAY)  # в очереди
    data = make_client(Role.SHOP_HEAD).get(DASHBOARD).data["production"]
    assert data["load"] == [{"department": world["shop"].pk, "name": "Пряничный цех", "planned": 1, "in_progress": 0, "done": 1}]
    row = data["output"][0]
    assert (row["output"], row["defect"], row["defect_percent"]) == (16, 4, D("20.0"))


def test_stock_summary(make_client, world):
    expired = stock.receive(world["flour"], D(2), on_date=TODAY - timedelta(days=10), expiry_date=TODAY - timedelta(days=1),
                            unit_cost=D(300))
    data = make_client(Role.STOREKEEPER).get("/api/reports/stock/").data
    assert data["raw_value"] == 2100 and data["expired_value"] == 600
    below = data["below_min"][0]
    assert (below["name"], below["available"], below["shortage"]) == ("Мука", 5, 45)  # просроченное не считается
    assert data["expiring"][0]["number"] == expired.number and data["expiring"][0]["status"] == "expired"


def test_report_permissions(make_client, world):
    assert make_client(Role.STOREKEEPER).get("/api/reports/sales/").status_code == 403
    assert make_client(Role.SALES).get("/api/reports/production/").status_code == 403
    assert make_client(Role.HR).get("/api/reports/stock/").status_code == 403
    assert make_client(Role.ACCOUNTANT).get("/api/reports/sales/?date_from=2026-01-01&date_to=2026-01-31").status_code == 200
