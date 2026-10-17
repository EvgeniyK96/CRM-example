from datetime import timedelta
from decimal import Decimal

import pytest
from django.utils import timezone

from apps.accounts.models import Role, User
from apps.catalog.models import Item, ItemKind, Supplier, Unit
from apps.hr.models import Department, Employee, Position
from apps.production.models import ProductionTask
from apps.purchasing.models import PurchaseOrder
from apps.recipes.models import Recipe, RecipeLine
from apps.recipes.services import activate
from apps.sales import services as sales
from apps.sales.models import Client, SalesOrder, SalesOrderLine
from apps.warehouse import services as stock
from apps.warehouse.models import MoveKind

D = Decimal
TODAY = timezone.localdate()
TASKS = "/api/production/tasks/"
DEMAND = "/api/production/demand/"


@pytest.fixture
def factory(db):
    """Цех, продукт «Пряник» (рецептура: 1 кг муки + 2 яйца на 10 шт), мука и яйца на складе."""
    kg = Unit.objects.create(code="кг", name="килограмм")
    pcs = Unit.objects.create(code="шт", name="штука", is_fractional=False)
    shop = Department.objects.create(name="Пряничный цех", is_production=True)
    other = Department.objects.create(name="Вафельный цех", is_production=True)
    flour = Item.objects.create(kind=ItemKind.RAW, code="R1", name="Мука", unit=kg, shelf_life_days=100)
    eggs = Item.objects.create(kind=ItemKind.RAW, code="R2", name="Яйцо", unit=pcs, shelf_life_days=20)
    ginger = Item.objects.create(kind=ItemKind.PRODUCT, code="P1", name="Пряник", unit=pcs, shelf_life_days=30,
                                 department=shop, sale_price=100)
    waffle = Item.objects.create(kind=ItemKind.PRODUCT, code="P2", name="Вафли", unit=pcs, shelf_life_days=90,
                                 department=other, sale_price=50)
    for product in (ginger, waffle):
        recipe = Recipe.objects.create(product=product, version=1, output_qty=10)
        RecipeLine.objects.create(recipe=recipe, ingredient=flour, quantity=1)
        RecipeLine.objects.create(recipe=recipe, ingredient=eggs, quantity=D("2.5"))
        activate(recipe)
    supplier = Supplier.objects.create(name="Поставщик")
    stock.receive(flour, D(5), on_date=TODAY, unit_cost=D(300), supplier=supplier)
    stock.receive(eggs, D(100), on_date=TODAY, unit_cost=D(50), supplier=supplier)
    return {"shop": shop, "other": other, "flour": flour, "eggs": eggs, "ginger": ginger, "waffle": waffle}


@pytest.fixture
def boss(make_client):
    return make_client(Role.SHOP_HEAD)


def confirmed_order(item, qty, days=2):
    client = Client.objects.get_or_create(name="Магазин", defaults={"kind": "store"})[0]
    order = SalesOrder.objects.create(client=client, delivery_date=TODAY + timedelta(days=days))
    SalesOrderLine.objects.create(order=order, item=item, quantity=qty, price=100)
    return sales.confirm(order)


def create_task(api, product, qty="20"):
    r = api.post(TASKS, {"product": product.pk, "planned_qty": qty, "planned_date": str(TODAY)}, format="json")
    assert r.status_code == 201, r.data
    return r.data


# --- Планирование ------------------------------------------------------------


def test_manual_task_takes_department_and_active_recipe(boss, factory):
    task = create_task(boss, factory["ginger"])
    assert task["number"] == f"ПЗ-{task['id']:05d}"
    assert task["department_name"] == "Пряничный цех" and task["recipe_version"] == 1


def test_demand_and_planning_from_orders(boss, factory):
    first = confirmed_order(factory["ginger"], 30, days=3)
    second = confirmed_order(factory["ginger"], 20, days=2)
    demand = boss.get(DEMAND).data
    assert len(demand) == 1 and D(demand[0]["quantity"]) == 50

    tasks = boss.post(DEMAND).data
    assert len(tasks) == 1
    task = tasks[0]
    assert D(task["planned_qty"]) == 50
    assert task["planned_date"] == str(TODAY + timedelta(days=1))  # накануне ближайшей отгрузки
    assert {D(a["quantity"]) for a in task["allocations"]} == {30, 20}
    assert set(SalesOrder.objects.filter(pk__in=[first.pk, second.pk]).values_list("status", flat=True)) == {"in_production"}
    assert boss.get(DEMAND).data == []  # всё покрыто заданиями
    assert boss.post(DEMAND).status_code == 400


def test_cancel_task_returns_orders_to_confirmed(boss, factory):
    order = confirmed_order(factory["ginger"], 10)
    task = boss.post(DEMAND).data[0]
    assert boss.post(f"{TASKS}{task['id']}/cancel/").data["status"] == "cancelled"
    assert SalesOrder.objects.get(pk=order.pk).status == "confirmed"
    assert D(boss.get(DEMAND).data[0]["quantity"]) == 10  # потребность снова непокрыта


# --- Запуск ------------------------------------------------------------------


def test_requirements_round_discrete_units(boss, factory):
    task = create_task(boss, factory["ginger"], qty="15")
    rows = {r["ingredient_name"]: r for r in boss.get(f"{TASKS}{task['id']}/requirements/").data}
    assert D(rows["Мука"]["quantity"]) == D("1.5")
    assert D(rows["Яйцо"]["quantity"]) == 4  # 2.5 × 1.5 = 3.75 → 4 целых яйца


def test_start_consumes_raw_fefo(boss, factory):
    task = create_task(boss, factory["ginger"], qty="20")
    r = boss.post(f"{TASKS}{task['id']}/start/")
    assert r.status_code == 200 and r.data["status"] == "in_progress"
    assert stock.available_qty(factory["flour"]) == 3 and stock.available_qty(factory["eggs"]) == 95
    consumed = {c["item_name"]: D(c["quantity"]) for c in boss.get(f"{TASKS}{task['id']}/consumptions/").data}
    assert consumed == {"Мука": 2, "Яйцо": 5}


def test_start_with_shortage_consumes_nothing(boss, factory):
    task = create_task(boss, factory["ginger"], qty="60")  # муки нужно 6 кг, есть 5
    r = boss.post(f"{TASKS}{task['id']}/start/")
    assert r.status_code == 400 and "Мука" in r.data["detail"]
    assert stock.available_qty(factory["flour"]) == 5 and stock.available_qty(factory["eggs"]) == 100
    assert ProductionTask.objects.get(pk=task["id"]).status == "planned"


def test_request_purchase_for_shortage(boss, factory):
    task = create_task(boss, factory["ginger"], qty="60")
    r = boss.post(f"{TASKS}{task['id']}/request_purchase/")
    assert r.status_code == 201 and r.data["skipped"] == []
    order = PurchaseOrder.objects.get()
    line = order.lines.get()
    assert (order.status, line.item, line.quantity, line.price) == ("draft", factory["flour"], 1, 300)


# --- Завершение --------------------------------------------------------------


def test_finish_creates_lot_with_cost_and_fulfills_orders(boss, factory):
    early = confirmed_order(factory["ginger"], 8, days=1)
    late = confirmed_order(factory["ginger"], 12, days=3)
    task = boss.post(DEMAND).data[0]
    boss.post(f"{TASKS}{task['id']}/start/")  # 2 кг муки × 300 + 5 яиц × 50 = 850

    # выпустили меньше плана: 15 из 20, 1 в брак
    r = boss.post(f"{TASKS}{task['id']}/finish/", {"actual_qty": "15", "defect_qty": "1"}, format="json")
    assert r.status_code == 200, r.data
    assert r.data["status"] == "done" and D(r.data["raw_cost"]) == 850
    assert D(r.data["unit_cost"]) == D("56.67")  # 850 / 15 годных
    assert stock.available_qty(factory["ginger"]) == 15

    # сначала заказ с ранней отгрузкой (8), остаток 7 — второму
    assert SalesOrder.objects.get(pk=early.pk).status == "ready"
    late_line = SalesOrderLine.objects.get(order=late)
    assert (late_line.reserved_qty, late_line.to_produce) == (7, 5)
    assert SalesOrder.objects.get(pk=late.pk).status == "confirmed"  # 5 шт ждут нового задания
    assert D(boss.get(DEMAND).data[0]["quantity"]) == 5


def test_finish_validation(boss, factory):
    task = create_task(boss, factory["ginger"])
    assert boss.post(f"{TASKS}{task['id']}/finish/", {"actual_qty": "1"}, format="json").status_code == 400  # не запущено
    boss.post(f"{TASKS}{task['id']}/start/")
    assert boss.post(f"{TASKS}{task['id']}/finish/", {"actual_qty": "0"}, format="json").status_code == 400
    assert boss.post(f"{TASKS}{task['id']}/cancel/").status_code == 400  # сырьё уже списано


def test_trace_both_directions(boss, factory):
    task = create_task(boss, factory["ginger"], qty="10")
    boss.post(f"{TASKS}{task['id']}/start/")
    done = boss.post(f"{TASKS}{task['id']}/finish/", {"actual_qty": "10"}, format="json").data

    product_trace = boss.get(f"/api/production/trace/{done['output_lot']}/").data
    assert product_trace["produced_by"]["number"] == done["number"]
    assert {i["item_name"] for i in product_trace["ingredients"]} == {"Мука", "Яйцо"}
    assert product_trace["ingredients"][0]["supplier_name"] == "Поставщик"

    flour_lot = factory["flour"].lots.get()
    raw_trace = boss.get(f"/api/production/trace/{flour_lot.pk}/").data
    assert raw_trace["used_in"][0]["output_lot"]["number"] == done["output_lot_number"]


# --- Права -------------------------------------------------------------------


def shop_head_of(department, username):
    user = User.objects.create_user(username=username, password="x", role=Role.SHOP_HEAD)
    Employee.objects.create(user=user, last_name=username, first_name="x", department=department,
                            position=Position.objects.get_or_create(name="Начальник цеха")[0], hire_date=TODAY)
    from rest_framework.test import APIClient

    api = APIClient()
    api.force_authenticate(user)
    return api


def test_shop_head_limited_to_own_department(boss, factory):
    ginger_head = shop_head_of(factory["shop"], "ginger_head")
    waffle_task = create_task(boss, factory["waffle"])  # начальник производства может всё

    assert ginger_head.post(f"{TASKS}{waffle_task['id']}/start/").status_code == 403
    r = ginger_head.post(TASKS, {"product": factory["waffle"].pk, "planned_qty": "1", "planned_date": str(TODAY)},
                         format="json")
    assert r.status_code == 403
    assert ginger_head.get(f"{TASKS}{waffle_task['id']}/").status_code == 200  # смотреть можно

    confirmed_order(factory["ginger"], 5)
    confirmed_order(factory["waffle"], 5)
    assert [d["product_name"] for d in ginger_head.get(DEMAND).data] == ["Пряник"]
    me = ginger_head.get("/api/auth/users/me/").data
    assert me["department_name"] == "Пряничный цех"


def test_other_roles_read_only(make_client, factory):
    sales_api = make_client(Role.SALES)
    assert sales_api.get(TASKS).status_code == 200
    payload = {"product": factory["ginger"].pk, "planned_qty": "1", "planned_date": str(TODAY)}
    assert sales_api.post(TASKS, payload, format="json").status_code == 403
    assert sales_api.post(DEMAND).status_code == 403


def test_task_validation(boss, factory):
    flour = factory["flour"]
    assert boss.post(TASKS, {"product": flour.pk, "planned_qty": "1", "planned_date": str(TODAY)}, format="json").status_code == 400
    past = str(TODAY - timedelta(days=1))
    assert boss.post(TASKS, {"product": factory["ginger"].pk, "planned_qty": "1", "planned_date": past}, format="json").status_code == 400
    Recipe.objects.filter(product=factory["ginger"]).update(status="archived")
    r = boss.post(TASKS, {"product": factory["ginger"].pk, "planned_qty": "1", "planned_date": str(TODAY)}, format="json")
    assert r.status_code == 400 and "рецептуры" in str(r.data)


def test_seed_demo_production(db):
    from django.core.management import call_command

    call_command("seed_demo")
    statuses = sorted(ProductionTask.objects.values_list("status", flat=True))
    assert statuses.count("done") == 1 and statuses.count("in_progress") == 1
    assert stock.available_qty(Item.objects.get(code="PRD-007")) > 0
    assert MoveKind.PRODUCTION_IN in set(Item.objects.get(code="PRD-007").lots.values_list("moves__kind", flat=True))
