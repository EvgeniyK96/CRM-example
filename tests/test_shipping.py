from datetime import timedelta
from decimal import Decimal

import pytest
from django.utils import timezone

from apps.accounts.models import Role
from apps.catalog.models import Item, ItemKind, Unit
from apps.hr.models import Department
from apps.sales import services as sales
from apps.sales.models import Client, SalesOrder, SalesOrderLine, Shipment
from apps.warehouse import services as stock
from apps.warehouse.models import MoveKind, StockMove

D = Decimal
TODAY = timezone.localdate()
ORDERS = "/api/sales/orders/"


@pytest.fixture
def cake(db):
    pcs = Unit.objects.create(code="шт", name="штука", is_fractional=False)
    shop = Department.objects.create(name="Цех", is_production=True)
    return Item.objects.create(kind=ItemKind.PRODUCT, code="P1", name="Торт", unit=pcs, shelf_life_days=5,
                               department=shop, sale_price=1000)


@pytest.fixture
def store(make_client):
    return make_client(Role.STOREKEEPER)


def produced(item, qty, days_ago, cost):
    return stock.receive(item, D(qty), on_date=TODAY - timedelta(days=days_ago), unit_cost=D(cost),
                         kind=MoveKind.PRODUCTION_IN)


def ready_order(item, qty, client_name="Магазин"):
    client = Client.objects.get_or_create(name=client_name, defaults={"kind": "store", "tax_id": "123"})[0]
    order = SalesOrder.objects.create(client=client, delivery_date=TODAY, delivery_address="ул. Пекарная, 5")
    SalesOrderLine.objects.create(order=order, item=item, quantity=qty, price=900)
    order = sales.confirm(order)
    assert order.status == "ready"
    return order


def test_ship_consumes_fefo_and_closes_order(store, cake):
    old = produced(cake, 3, days_ago=3, cost=400)  # истекает раньше — уходит первой
    new = produced(cake, 10, days_ago=0, cost=500)
    order = ready_order(cake, 5)

    r = store.post(f"{ORDERS}{order.pk}/ship/", {"driver": "Сидоров"}, format="json")
    assert r.status_code == 201, r.data
    shipment = r.data
    assert shipment["number"] == f"ОТ-{shipment['id']:05d}" and shipment["driver"] == "Сидоров"
    assert [(i["lot_number"], D(i["quantity"])) for i in shipment["items"]] == [(old.number, 3), (new.number, 2)]
    assert D(shipment["total"]) == 4500 and D(shipment["cost"]) == 3 * 400 + 2 * 500

    assert SalesOrder.objects.get(pk=order.pk).status == "shipped"
    assert stock.lot_balance(old) == 0 and stock.lot_balance(new) == 8
    assert set(StockMove.objects.filter(quantity__lt=0).values_list("kind", flat=True)) == {MoveKind.SHIPMENT}

    order_data = store.get(f"{ORDERS}{order.pk}/").data
    assert order_data["shipment"] == shipment["id"] and order_data["shipment_number"] == shipment["number"]


def test_shipped_reservation_is_released(store, cake):
    produced(cake, 10, days_ago=0, cost=500)
    first = ready_order(cake, 6)
    store.post(f"{ORDERS}{first.pk}/ship/")
    # отгружено 6, на складе 4, резервов больше нет
    assert sales.free_stock(cake, TODAY) == 4


def test_only_ready_order_can_be_shipped(store, cake):
    client = Client.objects.create(name="Опт", kind="wholesale")
    order = SalesOrder.objects.create(client=client, delivery_date=TODAY)
    SalesOrderLine.objects.create(order=order, item=cake, quantity=1, price=1)
    r = store.post(f"{ORDERS}{order.pk}/ship/")
    assert r.status_code == 400 and Shipment.objects.count() == 0


def test_only_storekeeper_ships(make_client, cake):
    produced(cake, 5, days_ago=0, cost=1)
    order = ready_order(cake, 5)
    assert make_client(Role.SALES).post(f"{ORDERS}{order.pk}/ship/").status_code == 403
    assert make_client(Role.SALES).get("/api/sales/shipments/").status_code == 200


def test_ship_fails_if_stock_expired_after_confirmation(store, cake):
    lot = produced(cake, 5, days_ago=0, cost=1)
    order = ready_order(cake, 5)
    # продукция просрочилась (или списана) уже после подтверждения
    stock.write_off(lot, D(5), reason="брак")
    r = store.post(f"{ORDERS}{order.pk}/ship/")
    assert r.status_code == 400 and "верните заказ в работу" in r.data["detail"]
    assert Shipment.objects.count() == 0 and SalesOrder.objects.get(pk=order.pk).status == "ready"


def test_trace_reaches_client(store, cake):
    lot = produced(cake, 5, days_ago=0, cost=1)
    order = ready_order(cake, 4, client_name="Кофейня")
    shipment = store.post(f"{ORDERS}{order.pk}/ship/").data
    trace = store.get(f"/api/production/trace/{lot.pk}/").json()
    assert trace["shipped_to"] == [{
        "shipment": shipment["id"], "shipment_number": shipment["number"], "date": str(TODAY),
        "order": order.pk, "order_number": order.number, "client_name": "Кофейня", "quantity": "4.000",
    }]


def test_shipments_journal_filters(store, cake):
    produced(cake, 10, days_ago=0, cost=1)
    a = ready_order(cake, 2, client_name="А")
    ready_order(cake, 3, client_name="Б")
    store.post(f"{ORDERS}{a.pk}/ship/")
    assert store.get("/api/sales/shipments/").data["count"] == 1
    assert store.get(f"/api/sales/shipments/?client={a.client_id}").data["count"] == 1
    assert store.get(f"/api/sales/shipments/?date_from={TODAY + timedelta(days=1)}").data["count"] == 0


def test_seed_demo_ships_ready_orders(db):
    from django.core.management import call_command

    call_command("seed_demo")
    assert Shipment.objects.count() >= 1
    assert not SalesOrder.objects.filter(status="ready").exists()
