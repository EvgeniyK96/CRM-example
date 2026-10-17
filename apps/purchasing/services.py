"""Закупки: жизненный цикл заявки поставщику и проведение приёмки на склад."""

from decimal import Decimal

from django.db import transaction
from django.db.models import Sum
from django.utils import timezone

from apps.warehouse import services as stock
from apps.warehouse.models import MoveKind
from core.exceptions import DomainError

from . import signals
from .models import PurchaseOrder, PurchaseOrderLine, Receipt, ReceiptLine

Status = PurchaseOrder.Status


class PurchasingError(DomainError):
    pass


def _lock(model, obj):
    return model.objects.select_for_update().get(pk=obj.pk)


def received_qty(order_line: PurchaseOrderLine) -> Decimal:
    """Сколько по строке заявки уже принято проведёнными приёмками."""
    total = order_line.receipt_lines.filter(receipt__status=Receipt.Status.POSTED).aggregate(s=Sum("quantity"))["s"]
    return total or Decimal(0)


@transaction.atomic
def send(order: PurchaseOrder) -> PurchaseOrder:
    order = _lock(PurchaseOrder, order)
    if order.status != Status.DRAFT:
        raise PurchasingError("Отправить можно только черновик заявки.")
    if not order.lines.exists():
        raise PurchasingError("В заявке нет ни одной строки.")
    order.status = Status.SENT
    order.save(update_fields=["status"])
    return order


@transaction.atomic
def cancel(order: PurchaseOrder) -> PurchaseOrder:
    order = _lock(PurchaseOrder, order)
    if order.status not in (Status.DRAFT, Status.SENT):
        raise PurchasingError("Отменить можно только черновик или отправленную заявку без поступлений.")
    if order.receipts.filter(status=Receipt.Status.POSTED).exists():
        raise PurchasingError("По заявке уже есть проведённые приёмки.")
    order.receipts.filter(status=Receipt.Status.DRAFT).delete()
    order.status = Status.CANCELLED
    order.save(update_fields=["status"])
    return order


@transaction.atomic
def create_receipt(order: PurchaseOrder, user=None) -> Receipt:
    """Черновик приёмки по заявке: в строки подставляется ещё не полученное количество."""
    order = _lock(PurchaseOrder, order)
    if order.status not in (Status.SENT, Status.PARTIAL):
        raise PurchasingError("Принять можно только отправленную заявку.")
    remaining = [
        (line, line.quantity - received_qty(line)) for line in order.lines.select_related("item")
    ]
    remaining = [(line, qty) for line, qty in remaining if qty > 0]
    if not remaining:
        raise PurchasingError("По заявке всё уже получено.")
    receipt = Receipt.objects.create(supplier=order.supplier, order=order, created_by=user)
    ReceiptLine.objects.bulk_create(
        ReceiptLine(receipt=receipt, item=line.item, quantity=qty, price=line.price, order_line=line)
        for line, qty in remaining
    )
    return receipt


def refresh_order_status(order: PurchaseOrder) -> None:
    lines = list(order.lines.all())
    received = [received_qty(line) for line in lines]
    if all(r >= line.quantity for r, line in zip(received, lines)):
        order.status = Status.RECEIVED
    elif any(r > 0 for r in received):
        order.status = Status.PARTIAL
    order.save(update_fields=["status"])


@transaction.atomic
def post_receipt(receipt: Receipt, user=None) -> Receipt:
    """Проводит приёмку: по каждой строке создаётся партия и движение прихода."""
    receipt = _lock(Receipt, receipt)
    if receipt.status != Receipt.Status.DRAFT:
        raise PurchasingError("Приёмка уже проведена.")
    lines = list(receipt.lines.select_related("item__unit", "order_line"))
    if not lines:
        raise PurchasingError("В приёмке нет ни одной строки.")
    if receipt.order and receipt.order.status not in (Status.SENT, Status.PARTIAL):
        raise PurchasingError("Заявка, по которой создана приёмка, не ожидает поставки.")

    for line in lines:
        try:
            line.lot = stock.receive(
                line.item, line.quantity, on_date=receipt.date, expiry_date=line.expiry_date,
                unit_cost=line.price, supplier=receipt.supplier, kind=MoveKind.RECEIPT,
                reference=f"Приёмка {receipt.number}", user=user,
            )
        except stock.StockError as e:
            raise PurchasingError(f"{line.item.name}: {e}")
        line.expiry_date = line.lot.expiry_date
        line.save(update_fields=["lot", "expiry_date"])

    receipt.status = Receipt.Status.POSTED
    receipt.posted_by = user
    receipt.posted_at = timezone.now()
    receipt.save(update_fields=["status", "posted_by", "posted_at"])

    if receipt.order:
        refresh_order_status(_lock(PurchaseOrder, receipt.order))
    signals.receipt_posted.send(sender=Receipt, receipt=receipt)
    return receipt
