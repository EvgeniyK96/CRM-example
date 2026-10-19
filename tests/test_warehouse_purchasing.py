from datetime import timedelta
from decimal import Decimal

import pytest
from django.utils import timezone

from apps.accounts.models import Role
from apps.catalog.models import Item, ItemKind, Supplier, Unit
from apps.purchasing.models import PurchaseOrder, Receipt
from apps.warehouse import services as stock
from apps.warehouse.models import Lot, MoveKind, StockMove

D = Decimal
TODAY = timezone.localdate()


@pytest.fixture
def flour(db):
    kg = Unit.objects.create(code="кг", name="килограмм")
    return Item.objects.create(kind=ItemKind.RAW, code="R1", name="Мука", unit=kg, shelf_life_days=100, min_stock=50)


@pytest.fixture
def supplier(db):
    return Supplier.objects.create(name="ТОО Мука")


@pytest.fixture
def store(make_client):
    return make_client(Role.STOREKEEPER)


def lot(item, qty, days_ago=0, expires_in=None):
    on_date = TODAY - timedelta(days=days_ago)
    expiry = TODAY + timedelta(days=expires_in) if expires_in is not None else None
    return stock.receive(item, D(qty), on_date=on_date, expiry_date=expiry)


# --- Склад: сервисы --------------------------------------------------------


def test_receive_creates_lot_with_default_expiry(flour):
    new = lot(flour, 10, days_ago=5)
    assert new.number == f"П-{new.pk:06d}"
    assert new.expiry_date == TODAY - timedelta(days=5) + timedelta(days=100)
    assert stock.lot_balance(new) == 10


def test_fefo_takes_nearest_expiry_first_and_splits(flour):
    late = lot(flour, 10, expires_in=30)
    early = lot(flour, 5, expires_in=3)
    taken = stock.consume_fefo(flour, D(8), kind=MoveKind.PRODUCTION_OUT)
    assert [(t.lot, t.quantity) for t in taken] == [(early, 5), (late, 3)]
    assert stock.lot_balance(early) == 0 and stock.lot_balance(late) == 7


def test_fefo_skips_expired_lots(flour):
    expired = stock.receive(flour, D(100), on_date=TODAY - timedelta(days=10), expiry_date=TODAY - timedelta(days=1))
    fresh = lot(flour, 5)
    assert stock.available_qty(flour) == 5
    with pytest.raises(stock.InsufficientStock) as e:
        stock.consume_fefo(flour, D(6), kind=MoveKind.PRODUCTION_OUT)
    assert e.value.available == 5
    assert StockMove.objects.filter(quantity__lt=0).count() == 0  # ничего не списано
    assert stock.lot_balance(expired) == 100 and stock.lot_balance(fresh) == 5


def test_write_off_checks_balance(flour):
    batch = lot(flour, 5)
    with pytest.raises(stock.StockError):
        stock.write_off(batch, D(6), reason="брак")
    stock.write_off(batch, D(2), reason="брак")
    assert stock.lot_balance(batch) == 3


def test_expiry_status(flour):
    assert stock.expiry_status(lot(flour, 1, expires_in=60))[0] == "ok"
    assert stock.expiry_status(lot(flour, 1, expires_in=20))[0] == "expiring"  # ≤ 25% от 100 дней
    expired = stock.receive(flour, D(1), on_date=TODAY - timedelta(days=5), expiry_date=TODAY - timedelta(days=1))
    assert stock.expiry_status(expired) == ("expired", -1)


# --- Склад: API ------------------------------------------------------------


def test_stock_summary(store, flour):
    lot(flour, 30)
    stock.receive(flour, D(15), on_date=TODAY - timedelta(days=10), expiry_date=TODAY - timedelta(days=1))
    row = store.get("/api/warehouse/stock/?kind=raw").data["results"][0]
    assert (D(row["balance"]), D(row["available"]), D(row["expired"])) == (45, 30, 15)
    assert row["below_min"] is True  # доступно 30 < минимума 50
    assert store.get("/api/warehouse/stock/?below_min=false").data["count"] == 0


def test_lots_api_and_write_off(store, make_client, flour):
    batch = lot(flour, 10)
    data = store.get("/api/warehouse/lots/?in_stock=true").data["results"]
    assert data[0]["number"] == batch.number and data[0]["expiry_status"] == "ok"

    url = f"/api/warehouse/lots/{batch.pk}/write_off/"
    assert make_client(Role.SALES).post(url, {"quantity": "1", "reason": "x"}, format="json").status_code == 403
    r = store.post(url, {"quantity": "11", "reason": "брак"}, format="json")
    assert r.status_code == 400 and "detail" in r.data
    r = store.post(url, {"quantity": "4", "reason": "брак"}, format="json")
    assert r.status_code == 200 and D(r.data["balance"]) == 6

    moves = store.get(f"/api/warehouse/moves/?item={flour.pk}&kind=write_off").data["results"]
    assert [(D(m["quantity"]), m["reference"]) for m in moves] == [(-4, "брак")]


# --- Закупки ---------------------------------------------------------------


ORDERS = "/api/purchasing/orders/"
RECEIPTS = "/api/purchasing/receipts/"


def create_order(client, supplier, flour, qty="100"):
    payload = {"supplier": supplier.pk, "lines": [{"item": flour.pk, "quantity": qty, "price": "350"}]}
    r = client.post(ORDERS, payload, format="json")
    assert r.status_code == 201, r.data
    return r.data


def test_order_lifecycle(store, supplier, flour):
    order = create_order(store, supplier, flour)
    assert order["number"] == f"ЗП-{order['id']:05d}" and order["total"] == "35000.00"

    assert store.post(f"{ORDERS}{order['id']}/receive/").status_code == 400  # ещё черновик
    assert store.post(f"{ORDERS}{order['id']}/send/").data["status"] == "sent"
    assert store.patch(f"{ORDERS}{order['id']}/", {"comment": "x"}, format="json").status_code == 400

    # первая приёмка — частичная
    receipt = store.post(f"{ORDERS}{order['id']}/receive/").data
    assert receipt["lines"][0]["quantity"] == "100.000"
    line = {**receipt["lines"][0], "quantity": "60"}
    assert store.patch(f"{RECEIPTS}{receipt['id']}/", {"lines": [line]}, format="json").status_code == 200
    posted = store.post(f"{RECEIPTS}{receipt['id']}/post/").data
    assert posted["status"] == "posted" and posted["lines"][0]["lot_number"]
    assert PurchaseOrder.objects.get(pk=order["id"]).status == "partial"

    # вторая приёмка подставляет оставшиеся 40
    receipt2 = store.post(f"{ORDERS}{order['id']}/receive/").data
    assert receipt2["lines"][0]["quantity"] == "40.000"
    store.post(f"{RECEIPTS}{receipt2['id']}/post/")
    assert PurchaseOrder.objects.get(pk=order["id"]).status == "received"
    assert stock.available_qty(flour) == 100
    assert store.post(f"{ORDERS}{order['id']}/receive/").status_code == 400


def test_receipt_keeps_order_link_when_client_omits_it(store, supplier, flour):
    order = create_order(store, supplier, flour)
    store.post(f"{ORDERS}{order['id']}/send/")
    receipt = store.post(f"{ORDERS}{order['id']}/receive/").data
    # клиент присылает строку без order_line (как форма, которая не знает о скрытых полях)
    lines = [{"item": flour.pk, "quantity": "100", "price": "350"}]
    r = store.patch(f"{RECEIPTS}{receipt['id']}/", {"lines": lines}, format="json")
    assert r.data["lines"][0]["order_line"] is not None
    store.post(f"{RECEIPTS}{receipt['id']}/post/")
    assert PurchaseOrder.objects.get(pk=order["id"]).status == "received"


def test_receipt_without_order_and_immutability(store, supplier, flour):
    payload = {
        "supplier": supplier.pk, "date": str(TODAY),
        "lines": [{"item": flour.pk, "quantity": "25", "price": "300", "expiry_date": str(TODAY + timedelta(days=7))}],
    }
    receipt = store.post(RECEIPTS, payload, format="json").data
    store.post(f"{RECEIPTS}{receipt['id']}/post/")

    created = Lot.objects.get()
    assert (created.supplier, created.unit_cost, created.expiry_date) == (supplier, 300, TODAY + timedelta(days=7))
    assert store.post(f"{RECEIPTS}{receipt['id']}/post/").status_code == 400
    assert store.patch(f"{RECEIPTS}{receipt['id']}/", {"comment": "x"}, format="json").status_code == 400
    assert store.delete(f"{RECEIPTS}{receipt['id']}/").status_code == 400


def test_receipt_rejects_expiry_before_date(store, supplier, flour):
    payload = {
        "supplier": supplier.pk, "date": str(TODAY),
        "lines": [{"item": flour.pk, "quantity": "1", "expiry_date": str(TODAY - timedelta(days=1))}],
    }
    receipt = store.post(RECEIPTS, payload, format="json").data
    r = store.post(f"{RECEIPTS}{receipt['id']}/post/")
    assert r.status_code == 400 and Lot.objects.count() == 0
    assert Receipt.objects.get(pk=receipt["id"]).status == "draft"


def test_cannot_buy_finished_product(store, supplier, flour):
    product = Item.objects.create(kind=ItemKind.PRODUCT, code="P1", name="Торт", unit=flour.unit, shelf_life_days=3)
    r = store.post(ORDERS, {"supplier": supplier.pk, "lines": [{"item": product.pk, "quantity": "1"}]}, format="json")
    assert r.status_code == 400 and "lines" in r.data


def test_only_storekeeper_writes_purchasing(make_client, supplier, flour):
    payload = {"supplier": supplier.pk, "lines": [{"item": flour.pk, "quantity": "1"}]}
    assert make_client(Role.TECHNOLOGIST).post(ORDERS, payload, format="json").status_code == 403


def test_cancel_order(store, supplier, flour):
    order = create_order(store, supplier, flour)
    store.post(f"{ORDERS}{order['id']}/send/")
    store.post(f"{ORDERS}{order['id']}/receive/")  # черновик приёмки удалится при отмене
    assert store.post(f"{ORDERS}{order['id']}/cancel/").data["status"] == "cancelled"
    assert Receipt.objects.count() == 0


def test_filters_several_statuses_and_dates(store, supplier, flour):
    sent = create_order(store, supplier, flour)
    store.post(f"{ORDERS}{sent['id']}/send/")
    create_order(store, supplier, flour)  # черновик
    PurchaseOrder.objects.filter(pk=sent["id"]).update(expected_date=TODAY)

    def numbers(**params):
        return {o["number"] for o in store.get(ORDERS, params).data["results"]}

    assert len(numbers(status=["draft", "sent"])) == 2
    assert numbers(status="sent") == {sent["number"]}
    assert numbers(expected_from=TODAY, expected_to=TODAY) == {sent["number"]}
    assert numbers(expected_from=TODAY + timedelta(days=1)) == set()


def test_seed_demo(db):
    from django.core.management import call_command

    call_command("seed_demo")
    assert Receipt.objects.filter(status="posted").count() == 10
    assert PurchaseOrder.objects.get().status == "sent"
