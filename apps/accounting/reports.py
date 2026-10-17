"""Бухгалтерские отчёты по проводкам: ОСВ, карточка счёта, дебиторка, кредиторка, прибыли и убытки."""

from collections import defaultdict
from decimal import Decimal

from django.db.models import Q, Sum
from django.utils import timezone

from apps.catalog.models import Supplier
from apps.sales.models import Client

from . import chart as C
from .models import Account, Payment, Posting
from .services import invoices_with_paid, money

ZERO = Decimal(0)


def _turnovers(postings) -> tuple[dict, dict]:
    """Суммы по дебету и кредиту в разрезе счетов (округлены до копеек: SQLite отдаёт суммы с лишними знаками)."""
    debit = {r["debit"]: money(r["s"]) for r in postings.values("debit").annotate(s=Sum("amount"))}
    credit = {r["credit"]: money(r["s"]) for r in postings.values("credit").annotate(s=Sum("amount"))}
    return debit, credit


def _split(balance: Decimal) -> tuple[Decimal, Decimal]:
    """Сальдо → (дебетовое, кредитовое)."""
    return (balance, ZERO) if balance >= 0 else (ZERO, -balance)


def trial_balance(date_from, date_to) -> dict:
    """Оборотно-сальдовая ведомость за период."""
    before_d, before_c = _turnovers(Posting.objects.filter(entry__date__lt=date_from))
    period_d, period_c = _turnovers(Posting.objects.filter(entry__date__gte=date_from, entry__date__lte=date_to))

    rows, totals = [], defaultdict(lambda: ZERO)
    for account in Account.objects.all():
        opening = before_d.get(account.pk, ZERO) - before_c.get(account.pk, ZERO)
        turnover_d, turnover_c = period_d.get(account.pk, ZERO), period_c.get(account.pk, ZERO)
        if not (opening or turnover_d or turnover_c):
            continue
        closing = opening + turnover_d - turnover_c
        row = {"account": account.pk, "code": account.code, "name": account.name}
        row["opening_debit"], row["opening_credit"] = _split(opening)
        row["turnover_debit"], row["turnover_credit"] = turnover_d, turnover_c
        row["closing_debit"], row["closing_credit"] = _split(closing)
        for key in ("opening_debit", "opening_credit", "turnover_debit", "turnover_credit", "closing_debit", "closing_credit"):
            totals[key] += row[key]
        rows.append(row)
    return {"date_from": date_from, "date_to": date_to, "rows": rows, "totals": dict(totals)}


def account_card(account: Account, date_from, date_to, client_id=None, supplier_id=None) -> dict:
    """Карточка счёта: проводки с корреспондирующими счетами и нарастающим сальдо."""
    postings = Posting.objects.filter(Q(debit=account) | Q(credit=account))
    if client_id:
        postings = postings.filter(client_id=client_id)
    if supplier_id:
        postings = postings.filter(supplier_id=supplier_id)

    before = postings.filter(entry__date__lt=date_from)
    opening = money((before.filter(debit=account).aggregate(s=Sum("amount"))["s"] or ZERO) - (
        before.filter(credit=account).aggregate(s=Sum("amount"))["s"] or ZERO))

    balance, rows = opening, []
    period = (
        postings.filter(entry__date__gte=date_from, entry__date__lte=date_to)
        .select_related("entry", "debit", "credit", "client", "supplier").order_by("entry__date", "entry_id", "pk")
    )
    for p in period:
        is_debit = p.debit_id == account.pk
        balance += p.amount if is_debit else -p.amount
        corr = p.credit if is_debit else p.debit
        rows.append({
            "date": p.entry.date, "entry": p.entry_id, "description": p.entry.description,
            "source_type": p.entry.source_type, "source_id": p.entry.source_id,
            "corr_account": corr.code, "debit": p.amount if is_debit else None, "credit": None if is_debit else p.amount,
            "counterparty": (p.client or p.supplier).name if (p.client or p.supplier) else None, "balance": balance,
        })
    return {"account": account.code, "name": account.name, "opening": opening, "closing": balance, "rows": rows}


def receivables() -> dict:
    """Дебиторская задолженность по клиентам: выставлено, оплачено, долг, просрочено, аванс."""
    today = timezone.localdate()
    per_client = defaultdict(lambda: {"invoiced": ZERO, "overdue": ZERO, "open_invoices": 0})
    for inv in invoices_with_paid().select_related("client"):
        row = per_client[inv.client_id]
        row["invoiced"] += inv.amount
        remaining = inv.amount - inv.paid
        if remaining > 0:
            row["open_invoices"] += 1
            if inv.due_date < today:
                row["overdue"] += remaining
    paid = {
        r["client"]: money(r["s"])
        for r in Payment.objects.filter(direction=Payment.Direction.INCOMING).values("client").annotate(s=Sum("amount"))
    }
    clients = {c.pk: c for c in Client.objects.filter(pk__in=set(per_client) | set(paid))}
    rows = []
    for pk, client in clients.items():
        row = per_client[pk]
        balance = row["invoiced"] - paid.get(pk, ZERO)
        rows.append({
            "client": pk, "client_name": client.name, "invoiced": row["invoiced"], "paid": paid.get(pk, ZERO),
            "debt": max(balance, ZERO), "advance": max(-balance, ZERO), "overdue": row["overdue"],
            "open_invoices": row["open_invoices"],
        })
    rows.sort(key=lambda r: (-r["overdue"], -r["debt"]))
    return {"rows": rows, "total_debt": sum((r["debt"] for r in rows), ZERO),
            "total_overdue": sum((r["overdue"] for r in rows), ZERO)}


def payables() -> dict:
    """Кредиторская задолженность поставщикам по проводкам счёта 3310."""
    credit = {r["supplier"]: money(r["s"]) for r in Posting.objects.filter(credit__code=C.PAYABLES)
              .values("supplier").annotate(s=Sum("amount"))}
    debit = {r["supplier"]: money(r["s"]) for r in Posting.objects.filter(debit__code=C.PAYABLES)
             .values("supplier").annotate(s=Sum("amount"))}
    rows = []
    for supplier in Supplier.objects.filter(pk__in=set(credit) | set(debit)):
        received, paid = credit.get(supplier.pk, ZERO), debit.get(supplier.pk, ZERO)
        rows.append({"supplier": supplier.pk, "supplier_name": supplier.name, "received": received, "paid": paid,
                     "debt": received - paid})
    rows.sort(key=lambda r: -r["debt"])
    return {"rows": rows, "total_debt": sum((r["debt"] for r in rows), ZERO)}


def profit_and_loss(date_from, date_to) -> dict:
    """Отчёт о прибылях и убытках за период (по оборотам счетов доходов и расходов)."""
    period = Posting.objects.filter(entry__date__gte=date_from, entry__date__lte=date_to)
    debit, credit = _turnovers(period)
    accounts = {a.code: a for a in Account.objects.filter(type__in=("income", "expense"))}

    def turnover(code):
        a = accounts.get(code)
        if not a:
            return ZERO
        d, c = debit.get(a.pk, ZERO), credit.get(a.pk, ZERO)
        return c - d if a.type == "income" else d - c

    revenue, cost = turnover(C.REVENUE), turnover(C.COST_OF_SALES)
    admin, other = turnover(C.ADMIN_EXPENSES), turnover(C.OTHER_EXPENSES)
    gross = revenue - cost
    return {
        "date_from": date_from, "date_to": date_to,
        "revenue": revenue, "cost_of_sales": cost, "gross_profit": gross,
        "gross_margin": (gross / revenue * 100).quantize(Decimal("0.1")) if revenue else None,
        "admin_expenses": admin, "other_expenses": other, "net_profit": gross - admin - other,
    }
