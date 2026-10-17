"""
Производство: планирование заданий из заказов, запуск (списание сырья по рецептуре, FEFO),
завершение (выпуск партии, распределение по заказам), прослеживаемость партий.

Связь с заказами: строка заказа хранит to_produce — сколько ещё нужно произвести.
Открытые распределения (TaskAllocation) показывают, какая часть уже стоит в заданиях.
При выпуске произведённое переходит из to_produce в reserved_qty строки заказа.
"""

from datetime import timedelta
from decimal import ROUND_HALF_UP, Decimal

from django.db import transaction
from django.db.models import DecimalField, F, Q, Sum, Value
from django.db.models.functions import Coalesce
from django.utils import timezone

from apps.catalog.models import ItemKind
from apps.purchasing.models import PurchaseOrder, PurchaseOrderLine
from apps.recipes.models import Recipe
from apps.recipes.services import calculate
from apps.sales.models import SalesOrder, SalesOrderLine, ShipmentItem
from apps.warehouse import services as stock
from apps.warehouse.models import Lot, MoveKind
from core.exceptions import DomainError

from .models import ProductionTask, TaskAllocation, TaskConsumption

Status = ProductionTask.Status
CENT = Decimal("0.01")
QTY = DecimalField(max_digits=14, decimal_places=3)


class ProductionError(DomainError):
    pass


def _lock(task: ProductionTask) -> ProductionTask:
    return ProductionTask.objects.select_for_update().get(pk=task.pk)


def active_recipe(product) -> Recipe:
    recipe = Recipe.objects.filter(product=product, status=Recipe.Status.ACTIVE).first()
    if recipe is None:
        raise ProductionError(f"У продукта «{product.name}» нет активной рецептуры.")
    return recipe


def check_product(product) -> None:
    if product.kind != ItemKind.PRODUCT:
        raise ProductionError("Производить можно только готовую продукцию.")
    if not product.is_active:
        raise ProductionError("Продукт снят с производства.")
    if not product.department or not product.department.is_production:
        raise ProductionError("У продукта не указан цех-изготовитель.")


@transaction.atomic
def create_task(product, planned_qty: Decimal, planned_date, *, user=None, comment="") -> ProductionTask:
    check_product(product)
    return ProductionTask.objects.create(
        department=product.department, product=product, recipe=active_recipe(product),
        planned_qty=planned_qty, planned_date=planned_date, comment=comment, created_by=user,
    )


# --- Потребность из заказов ---------------------------------------------------


def _open_allocated():
    return Coalesce(
        Sum("allocations__quantity", filter=Q(allocations__task__status__in=ProductionTask.OPEN_STATUSES)),
        Value(Decimal(0)), output_field=QTY,
    )


def uncovered_lines(department_id=None):
    """Строки подтверждённых заказов, которые ещё не поставлены в задания полностью."""
    lines = (
        SalesOrderLine.objects
        .filter(order__status__in=(SalesOrder.Status.CONFIRMED, SalesOrder.Status.IN_PRODUCTION), to_produce__gt=0)
        .select_related("order__client", "item__unit", "item__department")
        .annotate(allocated=_open_allocated())
        .annotate(uncovered=F("to_produce") - F("allocated"))
        .filter(uncovered__gt=0)
        .order_by("order__delivery_date", "pk")
    )
    if department_id:
        lines = lines.filter(item__department_id=department_id)
    return lines


def demand(department_id=None) -> list[dict]:
    """Непокрытая потребность, сгруппированная по продуктам."""
    groups: dict[int, dict] = {}
    for line in uncovered_lines(department_id):
        item = line.item
        group = groups.setdefault(item.pk, {
            "product": item.pk, "product_name": item.name, "unit_code": item.unit.code,
            "department": item.department_id, "department_name": item.department.name if item.department else None,
            "quantity": Decimal(0), "earliest_date": line.order.delivery_date, "orders": [],
        })
        group["quantity"] += line.uncovered
        group["orders"].append({
            "order": line.order_id, "order_number": line.order.number, "client_name": line.order.client.name,
            "delivery_date": line.order.delivery_date, "quantity": line.uncovered,
        })
    return list(groups.values())


def refresh_order_status(order: SalesOrder) -> None:
    """Статус заказа по состоянию производства: готов / в производстве / ждёт планирования."""
    if order.status not in SalesOrder.OPEN_STATUSES:
        return
    if not order.lines.filter(to_produce__gt=0).exists():
        status = SalesOrder.Status.READY
    elif TaskAllocation.objects.filter(order_line__order=order, task__status__in=ProductionTask.OPEN_STATUSES).exists():
        status = SalesOrder.Status.IN_PRODUCTION
    else:
        status = SalesOrder.Status.CONFIRMED
    if status != order.status:
        order.status = status
        order.save(update_fields=["status"])


@transaction.atomic
def plan_from_demand(*, user=None, department_id=None) -> list[ProductionTask]:
    """Создаёт по заданию на каждый продукт с непокрытой потребностью; срок — накануне ближайшей отгрузки."""
    today = timezone.localdate()
    # Сначала блокируем заказы с потребностью, потом читаем её: менеджер не вернёт заказ в работу посреди планирования
    list(SalesOrder.objects.select_for_update().filter(
        status__in=(SalesOrder.Status.CONFIRMED, SalesOrder.Status.IN_PRODUCTION), lines__to_produce__gt=0,
    ).values_list("pk"))
    lines = list(uncovered_lines(department_id))
    if not lines:
        raise ProductionError("Нет непокрытой потребности из заказов.")

    by_product: dict[int, list[SalesOrderLine]] = {}
    for line in lines:
        by_product.setdefault(line.item_id, []).append(line)

    tasks = []
    for product_lines in by_product.values():
        product = product_lines[0].item
        earliest = min(line.order.delivery_date for line in product_lines)
        task = create_task(
            product, sum((line.uncovered for line in product_lines), Decimal(0)),
            max(today, earliest - timedelta(days=1)), user=user, comment="Сформировано из заказов",
        )
        TaskAllocation.objects.bulk_create(
            TaskAllocation(task=task, order_line=line, quantity=line.uncovered) for line in product_lines
        )
        tasks.append(task)

    for order in SalesOrder.objects.filter(pk__in={line.order_id for line in lines}):
        refresh_order_status(order)
    return tasks


# --- Запуск ------------------------------------------------------------------


def _ingredients(task: ProductionTask) -> dict:
    return {line.ingredient_id: line.ingredient for line in task.recipe.lines.select_related("ingredient__unit")}


def requirements(task: ProductionTask) -> list[dict]:
    """Сырьё на плановый выпуск: нужно, доступно (непросроченное), не хватает."""
    items = _ingredients(task)
    rows = []
    for line in calculate(task.recipe, task.planned_qty):
        available = stock.available_qty(items[line["ingredient"]])
        rows.append({**line, "available": available, "shortage": max(line["quantity"] - available, Decimal(0))})
    return rows


@transaction.atomic
def start(task: ProductionTask, user=None) -> ProductionTask:
    """Запуск: списывает всё сырьё по рецептуре (FEFO) или не списывает ничего."""
    task = _lock(task)
    if task.status != Status.PLANNED:
        raise ProductionError("Запустить можно только запланированное задание.")
    rows = requirements(task)
    shortages = [r for r in rows if r["shortage"] > 0]
    if shortages:
        details = "; ".join(f"{r['ingredient_name']} — не хватает {r['shortage'].normalize():f} {r['unit_code']}" for r in shortages)
        raise ProductionError(f"Недостаточно сырья: {details}.")

    items = _ingredients(task)
    for row in rows:
        for taken in stock.consume_fefo(
            items[row["ingredient"]], row["quantity"], kind=MoveKind.PRODUCTION_OUT, reference=f"Задание {task.number}", user=user
        ):
            TaskConsumption.objects.create(task=task, move=taken.move)

    task.status = Status.IN_PROGRESS
    task.started_by = user
    task.started_at = timezone.now()
    task.save(update_fields=["status", "started_by", "started_at"])
    return task


# --- Завершение --------------------------------------------------------------


def raw_cost(task: ProductionTask) -> Decimal:
    total = sum(
        (-c.move.quantity * c.move.lot.unit_cost for c in task.consumptions.select_related("move__lot")), Decimal(0)
    )
    return total.quantize(CENT, ROUND_HALF_UP)


@transaction.atomic
def finish(task: ProductionTask, actual_qty: Decimal, defect_qty: Decimal = Decimal(0), *, user=None,
           comment="") -> ProductionTask:
    """
    Завершение: выпуск партии (себестоимость = сырьё / годный выход) и распределение
    выпущенного по заказам — сначала тем, у кого отгрузка раньше.
    """
    task = _lock(task)
    if task.status != Status.IN_PROGRESS:
        raise ProductionError("Завершить можно только задание в работе.")
    if actual_qty < 0 or defect_qty < 0:
        raise ProductionError("Количество не может быть отрицательным.")
    if actual_qty + defect_qty == 0:
        raise ProductionError("Укажите выпуск или брак.")

    today = timezone.localdate()
    task.raw_cost = raw_cost(task)
    if actual_qty > 0:
        task.output_lot = stock.receive(
            task.product, actual_qty, on_date=today, unit_cost=(task.raw_cost / actual_qty).quantize(CENT, ROUND_HALF_UP),
            kind=MoveKind.PRODUCTION_IN, reference=f"Задание {task.number}", user=user,
        )

    remaining = actual_qty
    allocations = (
        task.allocations.select_related("order_line__order")
        .order_by("order_line__order__delivery_date", "pk")
    )
    lines = {line.pk: line for line in SalesOrderLine.objects.select_for_update().filter(allocations__task=task)}
    for allocation in allocations:
        line = lines[allocation.order_line_id]
        given = min(allocation.quantity, remaining, line.to_produce)
        allocation.fulfilled = given
        allocation.save(update_fields=["fulfilled"])
        if given > 0:
            line.reserved_qty += given
            line.to_produce -= given
            line.save(update_fields=["reserved_qty", "to_produce"])
        remaining -= given

    task.status = Status.DONE
    task.actual_qty = actual_qty
    task.defect_qty = defect_qty
    task.finished_by = user
    task.finished_at = timezone.now()
    if comment:
        task.comment = f"{task.comment}\n{comment}".strip()
    task.save(update_fields=["status", "actual_qty", "defect_qty", "raw_cost", "output_lot", "finished_by",
                             "finished_at", "comment"])

    for order in SalesOrder.objects.filter(lines__allocations__task=task).distinct():
        refresh_order_status(order)
    return task


@transaction.atomic
def cancel(task: ProductionTask) -> ProductionTask:
    task = _lock(task)
    if task.status != Status.PLANNED:
        raise ProductionError("Отменить можно только запланированное задание: сырьё по запущенному уже списано.")
    task.status = Status.CANCELLED
    task.save(update_fields=["status"])
    for order in SalesOrder.objects.filter(lines__allocations__task=task).distinct():
        refresh_order_status(order)
    return task


# --- Закупка недостающего ----------------------------------------------------


@transaction.atomic
def request_purchase(task: ProductionTask, user=None) -> tuple[list[PurchaseOrder], list[str]]:
    """
    Черновики заявок поставщикам на нехватку сырья по заданию.
    Поставщик и цена — из последней поставки этого сырья; без истории поставок позиция пропускается.
    """
    shortages = [r for r in requirements(task) if r["shortage"] > 0]
    if not shortages:
        raise ProductionError("Сырья достаточно — закупка не нужна.")

    by_supplier: dict[int, list[tuple[dict, Lot]]] = {}
    skipped = []
    for row in shortages:
        last = (
            Lot.objects.filter(item_id=row["ingredient"], supplier__isnull=False).select_related("supplier")
            .order_by("-date", "-pk").first()
        )
        if last is None:
            skipped.append(row["ingredient_name"])
            continue
        by_supplier.setdefault(last.supplier_id, []).append((row, last))

    orders = []
    for rows in by_supplier.values():
        order = PurchaseOrder.objects.create(
            supplier=rows[0][1].supplier, created_by=user, comment=f"Нехватка сырья для задания {task.number}",
        )
        PurchaseOrderLine.objects.bulk_create(
            PurchaseOrderLine(order=order, item_id=row["ingredient"], quantity=row["shortage"], price=lot.unit_cost)
            for row, lot in rows
        )
        orders.append(order)
    return orders, skipped


# --- Прослеживаемость --------------------------------------------------------


def trace(lot: Lot) -> dict:
    """
    Для партии продукции — из каких партий сырья она сделана и каким клиентам отгружена.
    Для партии сырья — в какие партии продукции она ушла.
    """
    def lot_info(x: Lot):
        return {"id": x.pk, "number": x.number, "item_name": x.item.name, "unit_code": x.item.unit.code,
                "date": x.date, "expiry_date": x.expiry_date, "supplier_name": x.supplier.name if x.supplier else None}

    result = {"lot": lot_info(lot), "produced_by": None, "ingredients": [], "used_in": [], "shipped_to": []}

    task = ProductionTask.objects.filter(output_lot=lot).first()
    if task:
        result["produced_by"] = {"id": task.pk, "number": task.number, "department_name": task.department.name,
                                 "recipe_version": task.recipe.version, "finished_at": task.finished_at}
        for c in task.consumptions.select_related("move__lot__item__unit", "move__lot__supplier"):
            result["ingredients"].append({**lot_info(c.move.lot), "quantity": -c.move.quantity})

    for c in TaskConsumption.objects.filter(move__lot=lot).select_related(
        "task__output_lot__item__unit", "task__output_lot__supplier", "move"
    ):
        result["used_in"].append({
            "task": c.task_id, "task_number": c.task.number, "quantity": -c.move.quantity,
            "output_lot": lot_info(c.task.output_lot) if c.task.output_lot else None,
        })

    for item in ShipmentItem.objects.filter(move__lot=lot).select_related("shipment__order__client", "move"):
        shipment = item.shipment
        result["shipped_to"].append({
            "shipment": shipment.pk, "shipment_number": shipment.number, "date": shipment.date,
            "order": shipment.order_id, "order_number": shipment.order.number,
            "client_name": shipment.order.client.name, "quantity": -item.move.quantity,
        })
    return result
