import pytest
from rest_framework.test import APIClient

from apps.accounts.models import Role, User
from apps.activity.models import Activity
from apps.catalog.models import Item, ItemKind, Unit
from apps.hr.models import Department
from apps.sales import services as sales_services
from apps.sales.models import Client, SalesOrder
from tests.test_sales import new_order, put_stock

FEED = "/api/activity/"
TARGET = "sales.salesorder"


@pytest.fixture
def cake(db):
    pcs = Unit.objects.create(code="шт", name="штука")
    shop = Department.objects.create(name="Цех", is_production=True)
    return Item.objects.create(kind=ItemKind.PRODUCT, code="P1", name="Торт", unit=pcs, shelf_life_days=4,
                               department=shop, sale_price=1000)


@pytest.fixture
def client_wholesale(db):
    return Client.objects.create(name="Опт", kind="wholesale")


def login(role, username=None):
    """Клиент с настоящим JWT: автора событий запоминает аутентификация (force_authenticate её обходит)."""
    username = username or f"jwt_{role}"
    user = User.objects.filter(username=username).first() or User.objects.create_user(
        username=username, password="pass12345", role=role, first_name=username.title()
    )
    api = APIClient()
    token = api.post("/api/auth/jwt/create/", {"username": username, "password": "pass12345"}).data["access"]
    api.credentials(HTTP_AUTHORIZATION=f"Bearer {token}")
    return api, user


def timeline(api, order_id):
    return api.get(FEED, {"target": TARGET, "target_id": order_id}).data["results"]


@pytest.fixture
def sales(db):
    return login(Role.SALES)


def test_created_and_status_events_with_author(sales, client_wholesale, cake):
    api, user = sales
    put_stock(cake, 20)
    order = new_order(api, client_wholesale, cake)
    assert api.post(f"/api/sales/orders/{order['id']}/confirm/").status_code == 200

    events = timeline(api, order["id"])
    assert [e["kind"] for e in events] == ["status", "created"]  # новые сверху
    status, created = events
    assert status["text"] == "Новый → Готов к отгрузке"
    assert (status["old_status"], status["new_status"]) == ("new", "ready")
    assert status["author"] == created["author"] == user.pk
    assert status["target"] == {"type": TARGET, "id": order["id"], "title": f"Заказ {order['number']}",
                                "path": f"/orders/{order['id']}"}
    assert not status["can_delete"]


def test_status_change_outside_request_has_no_author(sales, client_wholesale, cake):
    api, user = sales
    order = new_order(api, client_wholesale, cake)
    Activity.objects.all().delete()
    sales_services.cancel(SalesOrder.objects.get(pk=order["id"]))  # как из команды: запроса нет
    event = Activity.objects.get()
    assert event.kind == "status" and event.author is None and event.text == "Новый → Отменён"


def test_comments_and_posts(sales, client_wholesale, cake):
    api, user = sales
    order = new_order(api, client_wholesale, cake)
    r = api.post(FEED, {"target": TARGET, "target_id": order["id"], "text": "  Клиент просит к 9 утра  "})
    assert r.status_code == 201 and r.data["kind"] == "comment" and r.data["text"] == "Клиент просит к 9 утра"
    assert r.data["can_delete"] and r.data["author_name"] == user.first_name

    post = api.post(FEED, {"text": "Завтра санитарный день в пряничном цехе"}).data
    assert post["kind"] == "post" and post["target"] is None

    assert [e["kind"] for e in timeline(api, order["id"])] == ["comment", "created"]
    feed = api.get(FEED).data["results"]
    assert [e["kind"] for e in feed][:2] == ["post", "comment"]
    assert {e["kind"] for e in api.get(FEED, {"kind": ["comment", "post"]}).data["results"]} == {"comment", "post"}


def test_bad_targets(sales):
    api, _ = sales
    assert api.post(FEED, {"target": "payroll.payrollperiod", "target_id": 1, "text": "x"}).status_code == 400
    assert api.post(FEED, {"target": TARGET, "target_id": 999, "text": "x"}).status_code == 400
    assert api.post(FEED, {"text": "   "}).status_code == 400
    assert api.get(FEED, {"target": "hr.employee", "target_id": 1}).status_code == 400


def test_delete_own_records_only(sales, client_wholesale, cake):
    api, _ = sales
    order = new_order(api, client_wholesale, cake)
    comment = api.post(FEED, {"target": TARGET, "target_id": order["id"], "text": "мой"}).data
    event = Activity.objects.get(kind="created")

    other, _ = login(Role.STOREKEEPER)
    assert other.delete(f"{FEED}{comment['id']}/").status_code == 403
    assert api.delete(f"{FEED}{event.pk}/").status_code == 403
    assert api.delete(f"{FEED}{comment['id']}/").status_code == 204

    admin, _ = login(Role.ADMIN)
    post = other.post(FEED, {"text": "чужое"}).data
    assert admin.delete(f"{FEED}{post['id']}/").status_code == 204


def test_deleted_draft_keeps_history(sales, client_wholesale, cake):
    api, _ = sales
    order = new_order(api, client_wholesale, cake)
    assert api.delete(f"/api/sales/orders/{order['id']}/").status_code == 204
    entry = api.get(FEED).data["results"][0]
    assert entry["target"]["path"] is None and "удалён" in entry["target"]["title"]


def test_feed_query_count_does_not_grow(sales, client_wholesale, cake, django_assert_max_num_queries):
    api, _ = sales
    for _ in range(5):
        new_order(api, client_wholesale, cake)
    with django_assert_max_num_queries(12):
        assert len(api.get(FEED).data["results"]) == 5
