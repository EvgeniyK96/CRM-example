"""
Складские операции. Все изменения остатков идут только через эти функции.

Остаток не хранится, а считается как сумма движений. Чтобы два параллельных
расхода не списали одну и ту же партию дважды, перед расчётом блокируем партии
номенклатуры (SELECT ... FOR UPDATE; в SQLite запись и так последовательна).
"""

from dataclasses import dataclass
from datetime import date, timedelta
from decimal import Decimal

from django.db import transaction
from django.utils import timezone

from core.exceptions import DomainError

from .models import Lot, MoveKind, StockMove


class StockError(DomainError):
    pass


class InsufficientStock(StockError):
    def __init__(self, item, required: Decimal, available: Decimal):
        self.item, self.required, self.available = item, required, available
        super().__init__(
            f"Недостаточно «{item.name}»: нужно {required.normalize():f}, "
            f"доступно {available.normalize():f} {item.unit.code}."
        )


@dataclass
class Taken:
    lot: Lot
    quantity: Decimal
    move: StockMove


def default_expiry(item, on_date: date) -> date:
    return on_date + timedelta(days=item.shelf_life_days)


def lot_balance(lot: Lot) -> Decimal:
    return Lot.objects.with_balance().get(pk=lot.pk).balance


def available_qty(item, on_date: date | None = None) -> Decimal:
    """Сколько номенклатуры можно взять сейчас (без просроченных партий)."""
    return sum((lot.balance for lot in Lot.objects.filter(item=item).usable(on_date)), Decimal(0))


@transaction.atomic
def receive(item, quantity: Decimal, *, on_date: date, expiry_date: date | None = None, unit_cost=Decimal(0),
            supplier=None, kind=MoveKind.RECEIPT, reference="", user=None) -> Lot:
    """Приход: создаёт новую партию и положительное движение по ней."""
    if quantity <= 0:
        raise StockError("Количество прихода должно быть больше нуля.")
    expiry_date = expiry_date or default_expiry(item, on_date)
    if expiry_date < on_date:
        raise StockError("Срок годности не может быть раньше даты поступления.")
    lot = Lot.objects.create(
        item=item, supplier=supplier, date=on_date, expiry_date=expiry_date, unit_cost=unit_cost
    )
    StockMove.objects.create(lot=lot, kind=kind, quantity=quantity, reference=reference, created_by=user)
    return lot


@transaction.atomic
def consume_fefo(item, quantity: Decimal, *, kind: str, reference="", user=None,
                 on_date: date | None = None) -> list[Taken]:
    """
    Расход по FEFO: сначала партии с ближайшим сроком годности, просроченные пропускаются.
    Если доступного остатка не хватает — ничего не списывает и бросает InsufficientStock.
    """
    if quantity <= 0:
        raise StockError("Количество расхода должно быть больше нуля.")
    list(Lot.objects.select_for_update().filter(item=item).values_list("pk", flat=True))

    lots = list(Lot.objects.filter(item=item).usable(on_date))
    available = sum((lot.balance for lot in lots), Decimal(0))
    if available < quantity:
        raise InsufficientStock(item, quantity, available)

    taken, remaining = [], quantity
    for lot in lots:
        if remaining <= 0:
            break
        qty = min(lot.balance, remaining)
        move = StockMove.objects.create(lot=lot, kind=kind, quantity=-qty, reference=reference, created_by=user)
        taken.append(Taken(lot, qty, move))
        remaining -= qty
    return taken


@transaction.atomic
def write_off(lot: Lot, quantity: Decimal, *, reason: str, user=None) -> StockMove:
    """Списание с конкретной партии (брак, порча, просрочка) — в том числе просроченной."""
    if quantity <= 0:
        raise StockError("Количество списания должно быть больше нуля.")
    lot = Lot.objects.select_for_update().get(pk=lot.pk)
    balance = lot_balance(lot)
    if quantity > balance:
        raise StockError(f"На партии {lot.number} только {balance.normalize():f} {lot.item.unit.code}.")
    return StockMove.objects.create(
        lot=lot, kind=MoveKind.WRITE_OFF, quantity=-quantity, reference=reason, created_by=user
    )


def expiry_status(lot: Lot, today: date | None = None) -> tuple[str, int]:
    """
    Статус срока годности партии и сколько дней осталось.
    «Истекает» — когда осталось не больше четверти срока годности (минимум 1 день).
    """
    today = today or timezone.localdate()
    days_left = (lot.expiry_date - today).days
    if days_left < 0:
        return "expired", days_left
    threshold = max(1, lot.item.shelf_life_days // 4)
    return ("expiring" if days_left <= threshold else "ok"), days_left
