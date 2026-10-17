"""
Заказы клиентов: цены, проверка наличия готовой продукции и резервирование.

Резерв — не движение по складу, а количество в строках открытых заказов (reserved_qty).
Свободный остаток = годная на дату отгрузки продукция − резервы других открытых заказов.
Фактическое списание партий (FEFO) произойдёт при отгрузке.
"""

from decimal import ROUND_HALF_UP, Decimal

from django.db import transaction
from django.db.models import Sum
from django.utils import timezone

from apps.catalog.models import Item
from apps.warehouse import services as stock
from apps.warehouse.models import MoveKind
from apps.warehouse.services import available_qty
from core.exceptions import DomainError

from .models import SalesOrder, SalesOrderLine, Shipment, ShipmentItem

Status = SalesOrder.Status
CENT = Decimal("0.01")


class SalesError(DomainError):
    pass


def list_price(item: Item, discount_percent: Decimal) -> Decimal:
    """Цена из прайса с учётом скидки клиента."""
    return (item.sale_price * (1 - discount_percent / 100)).quantize(CENT, ROUND_HALF_UP)


def reserved_qty(item, exclude_order=None) -> Decimal:
    lines = SalesOrderLine.objects.filter(item=item, order__status__in=SalesOrder.OPEN_STATUSES)
    if exclude_order is not None:
        lines = lines.exclude(order=exclude_order)
    return lines.aggregate(s=Sum("reserved_qty"))["s"] or Decimal(0)


def free_stock(item, on_date, exclude_order=None) -> Decimal:
    """Свободная готовая продукция, которая будет годна на дату on_date."""
    return max(available_qty(item, on_date) - reserved_qty(item, exclude_order), Decimal(0))


def check_date(order: SalesOrder) -> None:
    if order.delivery_date < timezone.localdate():
        raise SalesError("Дата отгрузки уже прошла — измените её.")


def availability(order: SalesOrder) -> list[dict]:
    """По каждой строке: сколько можно отгрузить со склада и сколько нужно произвести."""
    on_date = max(order.delivery_date, timezone.localdate())
    rows = []
    for line in order.lines.select_related("item__unit"):
        free = free_stock(line.item, on_date, exclude_order=order)
        from_stock = min(free, line.quantity)
        rows.append({
            "line": line.pk,
            "item": line.item_id,
            "item_name": line.item.name,
            "unit_code": line.item.unit.code,
            "quantity": line.quantity,
            "free_stock": free,
            "from_stock": from_stock,
            "to_produce": line.quantity - from_stock,
        })
    return rows


def _lock(order: SalesOrder) -> SalesOrder:
    return SalesOrder.objects.select_for_update().get(pk=order.pk)


@transaction.atomic
def confirm(order: SalesOrder, user=None) -> SalesOrder:
    """
    Подтверждает заказ: резервирует свободную продукцию, недостающее помечает «к производству».
    Всё есть на складе — заказ сразу готов к отгрузке.
    """
    order = _lock(order)
    if order.status != Status.NEW:
        raise SalesError("Подтвердить можно только новый заказ.")
    lines = list(order.lines.all())
    if not lines:
        raise SalesError("В заказе нет ни одной позиции.")
    check_date(order)

    # Блокируем продукцию заказа: параллельные подтверждения одних и тех же позиций
    # выполнятся по очереди и не зарезервируют один и тот же остаток дважды
    list(Item.objects.select_for_update().filter(pk__in=[line.item_id for line in lines]).values_list("pk"))

    for row in availability(order):
        SalesOrderLine.objects.filter(pk=row["line"]).update(reserved_qty=row["from_stock"], to_produce=row["to_produce"])

    order.status = Status.CONFIRMED if order.lines.filter(to_produce__gt=0).exists() else Status.READY
    order.confirmed_by = user
    order.confirmed_at = timezone.now()
    order.save(update_fields=["status", "confirmed_by", "confirmed_at"])
    return order


@transaction.atomic
def reopen(order: SalesOrder) -> SalesOrder:
    """Возвращает подтверждённый заказ в работу менеджеру; резервы снимаются."""
    order = _lock(order)
    if order.status not in (Status.CONFIRMED, Status.READY):
        raise SalesError("Вернуть в работу можно только подтверждённый заказ, по которому не начато производство.")
    order.lines.update(reserved_qty=0, to_produce=0)
    order.status = Status.NEW
    order.confirmed_by = None
    order.confirmed_at = None
    order.save(update_fields=["status", "confirmed_by", "confirmed_at"])
    return order


@transaction.atomic
def cancel(order: SalesOrder) -> SalesOrder:
    order = _lock(order)
    if order.status not in (Status.NEW, Status.CONFIRMED, Status.READY):
        raise SalesError("Этот заказ уже нельзя отменить.")
    order.lines.update(reserved_qty=0, to_produce=0)
    order.status = Status.CANCELLED
    order.save(update_fields=["status"])
    return order


@transaction.atomic
def ship(order: SalesOrder, user=None, *, vehicle="", driver="", comment="") -> Shipment:
    """
    Отгрузка готового заказа целиком: партии продукции списываются по FEFO (просроченные пропускаются),
    каждое списание привязывается к строке заказа. Резерв заказа после этого больше не учитывается.
    """
    order = _lock(order)
    if order.status != Status.READY:
        raise SalesError("Отгрузить можно только заказ, готовый к отгрузке.")

    shipment = Shipment.objects.create(
        order=order, date=timezone.localdate(), vehicle=vehicle, driver=driver, comment=comment, created_by=user,
    )
    reference = f"Отгрузка {shipment.number}, заказ {order.number}"
    for line in order.lines.select_related("item__unit"):
        try:
            taken = stock.consume_fefo(line.item, line.quantity, kind=MoveKind.SHIPMENT, reference=reference, user=user)
        except stock.InsufficientStock as e:
            raise SalesError(
                f"{e} Продукция могла просрочиться или быть списана после подтверждения заказа — "
                "верните заказ в работу и подтвердите заново."
            )
        ShipmentItem.objects.bulk_create(ShipmentItem(shipment=shipment, order_line=line, move=t.move) for t in taken)

    order.status = Status.SHIPPED
    order.save(update_fields=["status"])
    return shipment
