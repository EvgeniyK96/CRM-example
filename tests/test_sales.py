from datetime import timedelta
from decimal import Decimal

import pytest
from django.utils import timezone

from apps.accounts.models import Role
from apps.catalog.models import Item, ItemKind, Unit
from apps.hr.models import Department
from apps.sales.models import Client, SalesOrder
from apps.warehouse import services as stock
from apps.warehouse.models import MoveKind

D = Decimal
TODAY = timezone.localdate()
ORDERS = "/api/sales/orders/"


@pytest.fixture
def cake(db):
    pcs = Unit.objects.create(code="шт", name="штука")
    shop = Department.objects.create(name="Цех", is_production=True)
    return Item.objects.create(kind=ItemKind.PRODUCT, code="P1", name="Торт", unit=pcs, shelf_life_days=4,
                               department=shop, sale_price=1000)


@pytest.fixture
def client_wholesale(db):
    return Client.objects.create(name="Опт", kind="wholesale", discount_percent=10, delivery_address="Склад 1")


@pytest.fixture
def sales(make_client):
    return make_client(Role.SALES)


def put_stock(item, qty, produced_days_ago=0):
    return stock.receive(item, D(qty), on_date=TODAY - timedelta(days=produced_days_ago), kind=MoveKind.ADJUSTMENT)


def new_order(api, client, item, qty="10", days=1, **extra):
    payload = {"client": client.pk, "delivery_date": str(TODAY + timedelta(days=days)),
               "lines": [{"item": item.pk, "quantity": qty}], **extra}
    r = api.post(ORDERS, payload, format="json")
    assert r.status_code == 201, r.data
    return r.data


def test_order_defaults_from_client(sales, client_wholesale, cake):
    order = new_order(sales, client_wholesale, cake)
    assert order["number"] == f"ЗК-{order['id']:05d}"
    assert D(order["discount_percent"]) == 10 and order["delivery_address"] == "Склад 1"
    assert order["lines"][0]["price"] == "900.00" and order["total"] == "9000.00"


def test_explicit_price_and_discount_kept(sales, client_wholesale, cake):
    payload = {"client": client_wholesale.pk, "delivery_date": str(TODAY), "discount_percent": "0",
               "lines": [{"item": cake.pk, "quantity": "2", "price": "777"}]}
    order = sales.post(ORDERS, payload, format="json").data
    assert D(order["discount_percent"]) == 0 and order["lines"][0]["price"] == "777.00"


def test_order_validation(sales, client_wholesale, cake):
    raw = Item.objects.create(kind=ItemKind.RAW, code="R1", name="Мука", unit=cake.unit, shelf_life_days=100)
    bad = [
        {"delivery_date": str(TODAY - timedelta(days=1))},
        {"lines": [{"item": raw.pk, "quantity": "1"}]},
        {"lines": [{"item": cake.pk, "quantity": "0"}]},
        {"discount_percent": "100"},
    ]
    base = {"client": client_wholesale.pk, "delivery_date": str(TODAY), "lines": [{"item": cake.pk, "quantity": "1"}]}
    for patch in bad:
        assert sales.post(ORDERS, {**base, **patch}, format="json").status_code == 400, patch


def test_only_sales_writes(make_client, client_wholesale, cake):
    payload = {"client": client_wholesale.pk, "delivery_date": str(TODAY), "lines": []}
    store = make_client(Role.STOREKEEPER)
    assert store.post(ORDERS, payload, format="json").status_code == 403
    assert store.get(ORDERS).status_code == 200


def test_confirm_all_in_stock_makes_order_ready(sales, client_wholesale, cake):
    put_stock(cake, 15)
    order = new_order(sales, client_wholesale, cake, qty="10")
    r = sales.post(f"{ORDERS}{order['id']}/confirm/")
    assert r.data["status"] == "ready"
    line = r.data["lines"][0]
    assert (D(line["reserved_qty"]), D(line["to_produce"])) == (10, 0)
    assert r.data["confirmed_by_name"] == "u_sales"


def test_reservations_of_other_orders_are_respected(sales, client_wholesale, cake):
    put_stock(cake, 15)
    first = new_order(sales, client_wholesale, cake, qty="10")
    sales.post(f"{ORDERS}{first['id']}/confirm/")

    second = new_order(sales, client_wholesale, cake, qty="8")
    avail = sales.get(f"{ORDERS}{second['id']}/availability/").data[0]
    assert (D(avail["free_stock"]), D(avail["from_stock"]), D(avail["to_produce"])) == (5, 5, 3)

    r = sales.post(f"{ORDERS}{second['id']}/confirm/")
    assert r.data["status"] == "confirmed"
    assert (D(r.data["lines"][0]["reserved_qty"]), D(r.data["lines"][0]["to_produce"])) == (5, 3)

    # отмена первого заказа освобождает резерв
    sales.post(f"{ORDERS}{first['id']}/cancel/")
    third = new_order(sales, client_wholesale, cake, qty="10")
    assert D(sales.get(f"{ORDERS}{third['id']}/availability/").data[0]["free_stock"]) == 10


def test_stock_expiring_before_delivery_is_not_offered(sales, client_wholesale, cake):
    put_stock(cake, 10, produced_days_ago=2)  # торт годен 4 дня → истекает через 2 дня
    soon = new_order(sales, client_wholesale, cake, days=1)
    late = new_order(sales, client_wholesale, cake, days=3)
    assert D(sales.get(f"{ORDERS}{soon['id']}/availability/").data[0]["free_stock"]) == 10
    assert D(sales.get(f"{ORDERS}{late['id']}/availability/").data[0]["free_stock"]) == 0


def test_confirmed_order_is_locked_until_reopened(sales, client_wholesale, cake):
    order = new_order(sales, client_wholesale, cake)
    sales.post(f"{ORDERS}{order['id']}/confirm/")
    url = f"{ORDERS}{order['id']}/"
    assert sales.patch(url, {"comment": "x"}, format="json").status_code == 400
    assert sales.delete(url).status_code == 400
    assert sales.post(f"{url}confirm/").status_code == 400

    r = sales.post(f"{url}reopen/")
    assert r.data["status"] == "new" and D(r.data["lines"][0]["to_produce"]) == 0
    assert sales.patch(url, {"comment": "x"}, format="json").status_code == 200


def test_confirm_requires_lines(sales, client_wholesale, cake):
    order = sales.post(ORDERS, {"client": client_wholesale.pk, "delivery_date": str(TODAY)}, format="json").data
    r = sales.post(f"{ORDERS}{order['id']}/confirm/")
    assert r.status_code == 400 and "позиции" in r.data["detail"]


def test_confirm_rejects_past_delivery_date(sales, client_wholesale, cake):
    order = new_order(sales, client_wholesale, cake)
    SalesOrder.objects.filter(pk=order["id"]).update(delivery_date=TODAY - timedelta(days=1))
    assert sales.post(f"{ORDERS}{order['id']}/confirm/").status_code == 400


def test_mine_filter(make_client, client_wholesale, cake):
    alice, bob = make_client(Role.SALES), make_client(Role.ADMIN)
    new_order(alice, client_wholesale, cake)
    new_order(bob, client_wholesale, cake)
    assert alice.get(f"{ORDERS}?mine=true").data["count"] == 1
    assert alice.get(ORDERS).data["count"] == 2


def test_seed_sales(db):
    from django.core.management import call_command

    call_command("seed_sales")  # без производства: seed_demo дальше переводит заказы в «в производстве»
    statuses = list(SalesOrder.objects.order_by("pk").values_list("status", flat=True))
    assert statuses == ["ready", "confirmed", "confirmed", "new"]
