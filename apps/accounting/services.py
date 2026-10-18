"""
Автопроводки по хозяйственным операциям, счета покупателям и разнесение оплат.

Обработчики вызываются из сигналов доменных модулей (receivers.py) в той же транзакции,
что и сама операция: если проводка не создастся, откатится и операция.
Повторный вызов для того же документа ничего не делает (идемпотентность по source_type + source_id).
"""

from dataclasses import dataclass
from datetime import timedelta
from decimal import ROUND_HALF_UP, Decimal

from django.db import transaction
from django.db.models import DecimalField, Sum, Value
from django.db.models.functions import Coalesce
from django.utils import timezone

from apps.catalog.models import ItemKind
from core.exceptions import DomainError

from . import chart as C
from .models import Account, Invoice, JournalEntry, Payment, PaymentAllocation, Posting

Source = JournalEntry.Source
CENT = Decimal("0.01")
MONEY = DecimalField(max_digits=14, decimal_places=2)


class AccountingError(DomainError):
    pass


@dataclass
class Line:
    debit: str
    credit: str
    amount: Decimal
    client: object = None
    supplier: object = None
    comment: str = ""


def money(value) -> Decimal:
    return Decimal(value).quantize(CENT, ROUND_HALF_UP)


def local_date(dt):
    return timezone.localtime(dt).date() if dt else timezone.localdate()


def record(source_type: str, source_id: int | None, date, description: str, lines: list[Line], user=None):
    """Создаёт операцию с проводками; нулевые строки пропускаются. Для уже учтённого документа — ничего."""
    if source_id is not None:
        existing = JournalEntry.objects.filter(source_type=source_type, source_id=source_id).first()
        if existing:
            return existing
    lines = [line for line in lines if money(line.amount) > 0]
    if not lines:
        return None
    accounts = {a.code: a for a in Account.objects.filter(code__in={c for line in lines for c in (line.debit, line.credit)})}
    missing = {c for line in lines for c in (line.debit, line.credit)} - accounts.keys()
    if missing:
        raise AccountingError(f"В плане счетов нет счетов: {', '.join(sorted(missing))}.")
    entry = JournalEntry.objects.create(
        date=date, description=description[:255], source_type=source_type, source_id=source_id, created_by=user,
    )
    Posting.objects.bulk_create(
        Posting(entry=entry, debit=accounts[line.debit], credit=accounts[line.credit], amount=money(line.amount),
                client=line.client, supplier=line.supplier, comment=line.comment[:255])
        for line in lines
    )
    return entry


def stock_account(item) -> str:
    return C.RAW_MATERIALS if item.kind == ItemKind.RAW else C.FINISHED_GOODS


# --- Автопроводки по событиям --------------------------------------------------


def on_receipt_posted(receipt):
    amount = sum((line.quantity * line.price for line in receipt.lines.all()), Decimal(0))
    return record(Source.RECEIPT, receipt.pk, receipt.date, f"Приёмка {receipt.number}, {receipt.supplier.name}", [
        Line(C.RAW_MATERIALS, C.PAYABLES, amount, supplier=receipt.supplier, comment="Оприходовано сырьё"),
    ], receipt.posted_by)


def consumed_cost(task) -> Decimal:
    return money(sum(
        (-c.move.quantity * c.move.lot.unit_cost for c in task.consumptions.select_related("move__lot")), Decimal(0)
    ))


def on_task_started(task):
    return record(Source.PRODUCTION_START, task.pk, local_date(task.started_at), f"Запуск {task.number}: {task.product.name}", [
        Line(C.PRODUCTION, C.RAW_MATERIALS, consumed_cost(task), comment="Сырьё списано в производство"),
    ], task.started_by)


def on_task_finished(task):
    cost = task.raw_cost or Decimal(0)
    if task.output_lot_id:
        line = Line(C.FINISHED_GOODS, C.PRODUCTION, cost, comment=f"Выпуск {task.actual_qty.normalize():f} {task.product.unit.code}")
    else:
        line = Line(C.OTHER_EXPENSES, C.PRODUCTION, cost, comment="Вся партия ушла в брак")
    return record(Source.PRODUCTION_FINISH, task.pk, local_date(task.finished_at),
                  f"Выпуск {task.number}: {task.product.name}", [line], task.finished_by)


def shipment_amounts(shipment) -> tuple[Decimal, Decimal]:
    """(выручка, себестоимость) отгрузки."""
    items = list(shipment.items.select_related("order_line", "move__lot"))
    revenue = sum((-i.move.quantity * i.order_line.price for i in items), Decimal(0))
    cost = sum((-i.move.quantity * i.move.lot.unit_cost for i in items), Decimal(0))
    return money(revenue), money(cost)


def on_shipment_created(shipment):
    client = shipment.order.client
    revenue, cost = shipment_amounts(shipment)
    entry = record(Source.SHIPMENT, shipment.pk, shipment.date, f"Отгрузка {shipment.number}, {client.name}", [
        Line(C.RECEIVABLES, C.REVENUE, revenue, client=client, comment="Выручка от реализации"),
        Line(C.COST_OF_SALES, C.FINISHED_GOODS, cost, comment="Себестоимость отгруженной продукции"),
    ], shipment.created_by)
    if revenue > 0 and not Invoice.objects.filter(shipment=shipment).exists():
        Invoice.objects.create(
            client=client, shipment=shipment, date=shipment.date, amount=revenue,
            due_date=shipment.date + timedelta(days=client.payment_delay_days),
        )
        allocate(client)  # закрыть счёт авансами клиента, если они есть
    return entry


def on_stock_written_off(move):
    lot = move.lot
    return record(Source.WRITE_OFF, move.pk, local_date(move.created_at), f"Списание {lot.number}: {move.reference}", [
        Line(C.OTHER_EXPENSES, stock_account(lot.item), -move.quantity * lot.unit_cost, comment=lot.item.name),
    ], move.created_by)


def on_opening_balance(lot):
    quantity = lot.moves.aggregate(s=Sum("quantity"))["s"] or Decimal(0)
    return record(Source.OPENING, lot.pk, lot.date, f"Начальный остаток {lot.number}: {lot.item.name}", [
        Line(stock_account(lot.item), C.RETAINED_EARNINGS, quantity * lot.unit_cost),
    ])


def on_payment(payment):
    money_account = C.BANK if payment.method == Payment.Method.BANK else C.CASH
    if payment.direction == Payment.Direction.INCOMING:
        line = Line(money_account, C.RECEIVABLES, payment.amount, client=payment.client, comment=payment.comment)
        who = payment.client.name
    else:
        line = Line(C.PAYABLES, money_account, payment.amount, supplier=payment.supplier, comment=payment.comment)
        who = payment.supplier.name
    return record(Source.PAYMENT, payment.pk, payment.date, f"{payment.get_direction_display()} {payment.number}, {who}",
                  [line], payment.created_by)


# --- Счета и оплаты ----------------------------------------------------------


def _allocated(field):
    return Coalesce(Sum(f"{field}__amount"), Value(Decimal(0)), output_field=MONEY)


def invoices_with_paid():
    return Invoice.objects.annotate(paid=_allocated("allocations"))


@transaction.atomic
def allocate(client) -> None:
    """
    Разносит нераспределённые поступления клиента по его счетам:
    сначала на счёт, указанный в платеже, затем на самые ранние по сроку оплаты.
    Остаток платежа остаётся авансом и закроет следующий счёт.
    """
    incoming = Payment.objects.filter(client=client, direction=Payment.Direction.INCOMING)
    # Сначала блокируем платежи, потом отдельным запросом считаем разнесённое:
    # PostgreSQL не допускает FOR UPDATE вместе с агрегатом (GROUP BY)
    list(incoming.select_for_update().values_list("pk"))
    payments = list(incoming.annotate(allocated=_allocated("allocations")).order_by("date", "pk"))
    invoices = list(invoices_with_paid().filter(client=client).order_by("due_date", "pk"))
    remaining = {inv.pk: inv.amount - inv.paid for inv in invoices}
    by_pk = {inv.pk: inv for inv in invoices}

    new = []
    for payment in payments:
        free = payment.amount - payment.allocated
        targets = ([payment.invoice_id] if payment.invoice_id in by_pk else []) + [inv.pk for inv in invoices]
        for pk in dict.fromkeys(targets):  # без повторов, порядок сохраняется
            if free <= 0:
                break
            give = min(free, remaining[pk])
            if give > 0:
                new.append(PaymentAllocation(payment=payment, invoice=by_pk[pk], amount=give))
                remaining[pk] -= give
                free -= give
    PaymentAllocation.objects.bulk_create(new)


@transaction.atomic
def register_payment(payment: Payment) -> Payment:
    """Платёж создан — проводка и (для поступления) разнесение по счетам."""
    if payment.invoice_id and payment.invoice.client_id != payment.client_id:
        raise AccountingError("Счёт принадлежит другому клиенту.")
    on_payment(payment)
    if payment.direction == Payment.Direction.INCOMING:
        allocate(payment.client)
    return payment


@transaction.atomic
def create_manual_entry(date, description: str, lines: list[Line], user=None) -> JournalEntry:
    if not lines:
        raise AccountingError("Добавьте хотя бы одну проводку.")
    for line in lines:
        if line.debit == line.credit:
            raise AccountingError("Дебет и кредит проводки должны различаться.")
    return record(Source.MANUAL, None, date, description, lines, user)
