"""
Аналитика для дашборда и отчётов. Только чтение: агрегаты по продажам, производству, складу и деньгам.

Каждый раздел дашборда виден своим ролям (кладовщику не нужна выручка, менеджеру — брак цехов).
"""

from collections import defaultdict
from datetime import date, timedelta
from decimal import Decimal

from django.db.models import Count, Q, Sum
from django.utils import timezone

from apps.accounting.reports import receivables
from apps.accounts.models import Role
from apps.catalog.models import Item, ItemKind
from apps.production.models import ProductionTask
from apps.sales.models import SalesOrder, ShipmentItem
from apps.warehouse.models import Lot
from apps.warehouse.services import expiry_status

ZERO = Decimal(0)
CENT = Decimal("0.01")

# Раздел дашборда → роли, которым он показывается (администратор видит всё)
SECTIONS = {
    "sales": (Role.SALES, Role.ACCOUNTANT),
    "finance": (Role.ACCOUNTANT, Role.SALES),
    "production": (Role.SHOP_HEAD, Role.TECHNOLOGIST, Role.ACCOUNTANT),
    "warehouse": (Role.STOREKEEPER, Role.TECHNOLOGIST, Role.SHOP_HEAD),
}


def visible_sections(user) -> list[str]:
    return [name for name, roles in SECTIONS.items() if user.role == Role.ADMIN or user.role in roles]


def money(value) -> Decimal:
    return Decimal(value).quantize(CENT)


# --- Продажи ---------------------------------------------------------------------


def _shipped(date_from: date, date_to: date):
    """Строки отгрузок за период: (дата, продукт, клиент, количество, выручка, себестоимость)."""
    items = ShipmentItem.objects.filter(shipment__date__gte=date_from, shipment__date__lte=date_to).select_related(
        "shipment__order__client", "order_line__item__unit", "move__lot"
    )
    for i in items:
        qty = -i.move.quantity
        yield i.shipment.date, i.order_line.item, i.shipment.order.client, qty, qty * i.order_line.price, qty * i.move.lot.unit_cost


def sales_summary(date_from: date, date_to: date) -> dict:
    by_day: dict[date, Decimal] = defaultdict(lambda: ZERO)
    by_product: dict[int, dict] = {}
    by_client: dict[int, dict] = {}
    revenue = cost = ZERO
    for day, item, client, qty, rev, cst in _shipped(date_from, date_to):
        revenue += rev
        cost += cst
        by_day[day] += rev
        p = by_product.setdefault(item.pk, {"product": item.pk, "name": item.name, "unit_code": item.unit.code,
                                            "quantity": ZERO, "revenue": ZERO, "cost": ZERO})
        p["quantity"] += qty
        p["revenue"] += rev
        p["cost"] += cst
        c = by_client.setdefault(client.pk, {"client": client.pk, "name": client.name, "kind": client.kind,
                                             "revenue": ZERO, "cost": ZERO})
        c["revenue"] += rev
        c["cost"] += cst

    for row in (*by_product.values(), *by_client.values()):
        row["revenue"], row["cost"] = money(row["revenue"]), money(row["cost"])
        row["margin"] = row["revenue"] - row["cost"]
        row["margin_percent"] = (row["margin"] / row["revenue"] * 100).quantize(Decimal("0.1")) if row["revenue"] else None

    days = (date_to - date_from).days + 1
    return {
        "revenue": money(revenue), "cost": money(cost), "gross_profit": money(revenue - cost),
        # Ряд по всем дням периода, включая дни без отгрузок — иначе линия «перепрыгивает» нули
        "by_day": [{"date": date_from + timedelta(d), "revenue": money(by_day[date_from + timedelta(d)])}
                   for d in range(days)],
        "by_product": sorted(by_product.values(), key=lambda r: -r["revenue"]),
        "by_client": sorted(by_client.values(), key=lambda r: -r["revenue"]),
    }


def orders_by_status() -> dict:
    counts = dict(SalesOrder.objects.values_list("status").annotate(n=Count("pk")))
    return {status: counts.get(status, 0) for status, _ in SalesOrder.Status.choices}


# --- Производство ------------------------------------------------------------------


def production_summary(date_from: date, date_to: date) -> dict:
    """
    Загрузка цехов: в очереди и в работе — все открытые задания на сейчас, выполнено — завершённые за период.
    Выпуск и брак — по заданиям, завершённым в периоде.
    """
    done_in_period = Q(status=ProductionTask.Status.DONE, finished_at__date__gte=date_from, finished_at__date__lte=date_to)
    planned = (
        ProductionTask.objects.filter(Q(status__in=ProductionTask.OPEN_STATUSES) | done_in_period)
        .values("department_id", "department__name")
        .annotate(
            planned=Count("pk", filter=Q(status=ProductionTask.Status.PLANNED)),
            in_progress=Count("pk", filter=Q(status=ProductionTask.Status.IN_PROGRESS)),
            done=Count("pk", filter=done_in_period),
        )
        # order_by обязателен: иначе Meta.ordering модели попадёт в GROUP BY и разобьёт группы
        .order_by("department__name")
    )
    load = [{"department": r["department_id"], "name": r["department__name"], "planned": r["planned"],
             "in_progress": r["in_progress"], "done": r["done"]} for r in planned]

    finished = (
        ProductionTask.objects.filter(status=ProductionTask.Status.DONE, finished_at__date__gte=date_from,
                                      finished_at__date__lte=date_to)
        .values("product_id", "product__name", "product__unit__code", "department__name")
        .annotate(output=Sum("actual_qty"), defect=Sum("defect_qty"), raw_cost=Sum("raw_cost"), tasks=Count("pk"))
        .order_by("department__name", "product__name")
    )
    output = []
    for r in finished:
        total = (r["output"] or ZERO) + (r["defect"] or ZERO)
        output.append({
            "product": r["product_id"], "name": r["product__name"], "unit_code": r["product__unit__code"],
            "department_name": r["department__name"], "tasks": r["tasks"], "output": r["output"] or ZERO,
            "defect": r["defect"] or ZERO, "raw_cost": money(r["raw_cost"] or ZERO),
            "defect_percent": ((r["defect"] or ZERO) / total * 100).quantize(Decimal("0.1")) if total else Decimal("0.0"),
        })
    return {"load": load, "output": output}


# --- Склад -------------------------------------------------------------------------


def stock_summary() -> dict:
    """Оценка запасов по себестоимости партий, сырьё ниже минимума, партии с истекающим сроком."""
    today = timezone.localdate()
    lots = list(Lot.objects.with_balance().filter(balance__gt=0).select_related("item__unit"))

    per_item: dict[int, dict] = {}
    expiring = []
    value = {ItemKind.RAW: ZERO, ItemKind.PRODUCT: ZERO}
    expired_value = ZERO
    for lot in lots:
        item = lot.item
        status, days_left = expiry_status(lot, today)
        lot_value = lot.balance * lot.unit_cost
        value[item.kind] += lot_value
        row = per_item.setdefault(item.pk, {"item": item.pk, "code": item.code, "name": item.name, "kind": item.kind,
                                            "unit_code": item.unit.code, "quantity": ZERO, "available": ZERO,
                                            "value": ZERO, "min_stock": item.min_stock})
        row["quantity"] += lot.balance
        row["value"] += lot_value
        if status == "expired":
            expired_value += lot_value
        else:
            row["available"] += lot.balance
        if status != "ok":
            expiring.append({"lot": lot.pk, "number": lot.number, "name": item.name, "kind": item.kind,
                             "unit_code": item.unit.code, "balance": lot.balance, "expiry_date": lot.expiry_date,
                             "days_left": days_left, "status": status, "value": money(lot_value)})

    for row in per_item.values():
        row["value"] = money(row["value"])

    # Сырьё без остатков тоже бывает ниже минимума
    below_min = []
    for item in Item.objects.filter(kind=ItemKind.RAW, is_active=True, min_stock__gt=0).select_related("unit"):
        available = per_item.get(item.pk, {}).get("available", ZERO)
        if available < item.min_stock:
            below_min.append({"item": item.pk, "code": item.code, "name": item.name, "unit_code": item.unit.code,
                              "available": available, "min_stock": item.min_stock,
                              "shortage": item.min_stock - available})

    return {
        "raw_value": money(value[ItemKind.RAW]), "product_value": money(value[ItemKind.PRODUCT]),
        "expired_value": money(expired_value),
        "valuation": sorted(per_item.values(), key=lambda r: (r["kind"], -r["value"])),
        "expiring": sorted(expiring, key=lambda r: r["days_left"]),
        "below_min": sorted(below_min, key=lambda r: -(r["shortage"] / r["min_stock"])),
    }


# --- Дашборд -----------------------------------------------------------------------


def dashboard(user, date_from: date, date_to: date) -> dict:
    """Сводка для главной страницы — только разделы, доступные роли пользователя."""
    sections = visible_sections(user)
    result = {"date_from": date_from, "date_to": date_to, "sections": sections}

    if "sales" in sections:
        current = sales_summary(date_from, date_to)
        length = (date_to - date_from).days + 1
        prev = sales_summary(date_from - timedelta(days=length), date_from - timedelta(days=1))
        result["sales"] = {
            "revenue": current["revenue"], "revenue_prev": prev["revenue"], "gross_profit": current["gross_profit"],
            "by_day": current["by_day"], "top_products": current["by_product"][:8],
            "top_clients": current["by_client"][:8], "orders": orders_by_status(),
        }
    if "finance" in sections:
        r = receivables()
        result["finance"] = {"receivables": r["total_debt"], "overdue": r["total_overdue"]}
    if "production" in sections:
        result["production"] = production_summary(date_from, date_to)
    if "warehouse" in sections:
        stock = stock_summary()
        result["warehouse"] = {
            "raw_value": stock["raw_value"], "product_value": stock["product_value"],
            "expired_value": stock["expired_value"], "below_min": stock["below_min"], "expiring": stock["expiring"][:15],
        }
    return result
