from datetime import timedelta
from decimal import Decimal

import pytest
from django.core.management import call_command
from django.utils import timezone

from apps.accounting import chart as C
from apps.accounting import reports
from apps.accounting.models import Account, Invoice, JournalEntry, Posting
from apps.accounts.models import Role
from apps.catalog.models import Item, ItemKind, Supplier, Unit
from apps.hr.models import Department
from apps.production import services as production
from apps.purchasing import services as purchasing
from apps.purchasing.models import Receipt, ReceiptLine
from apps.recipes.models import Recipe, RecipeLine
from apps.recipes.services import activate
from apps.sales import services as sales
from apps.sales.models import Client, SalesOrder, SalesOrderLine, Shipment
from apps.warehouse import services as stock

D = Decimal
TODAY = timezone.localdate()
PAYMENTS = "/api/accounting/payments/"


def balance(code, **analytics) -> Decimal:
    """Сальдо счёта (дебет − кредит) по всем проводкам."""
    debit = sum((p.amount for p in Posting.objects.filter(debit__code=code, **analytics)), D(0))
    credit = sum((p.amount for p in Posting.objects.filter(credit__code=code, **analytics)), D(0))
    return debit - credit


@pytest.fixture
def world(db):
    """Мука 100 кг по 300 (приёмка), пряник: 1 кг муки на 10 шт, клиент с отсрочкой 10 дней."""
    kg = Unit.objects.create(code="кг", name="килограмм")
    pcs = Unit.objects.create(code="шт", name="штука", is_fractional=False)
    shop = Department.objects.create(name="Цех", is_production=True)
    flour = Item.objects.create(kind=ItemKind.RAW, code="R1", name="Мука", unit=kg, shelf_life_days=100)
    ginger = Item.objects.create(kind=ItemKind.PRODUCT, code="P1", name="Пряник", unit=pcs, shelf_life_days=30,
                                 department=shop, sale_price=100)
    recipe = Recipe.objects.create(product=ginger, version=1, output_qty=10)
    RecipeLine.objects.create(recipe=recipe, ingredient=flour, quantity=1)
    activate(recipe)
    supplier = Supplier.objects.create(name="Мелькомбинат")
    client = Client.objects.create(name="Опт", kind="wholesale", payment_delay_days=10)

    receipt = Receipt.objects.create(supplier=supplier, date=TODAY)
    ReceiptLine.objects.create(receipt=receipt, item=flour, quantity=100, price=300)
    purchasing.post_receipt(receipt)
    return {"flour": flour, "ginger": ginger, "supplier": supplier, "client": client, "receipt": receipt}


def produce(product, qty, actual=None, defect=0):
    task = production.create_task(product, D(qty), TODAY)
    production.start(task)
    return production.finish(task, D(actual if actual is not None else qty), D(defect))


def ship(client, product, qty, price=100):
    order = SalesOrder.objects.create(client=client, delivery_date=TODAY)
    SalesOrderLine.objects.create(order=order, item=product, quantity=qty, price=price)
    order = sales.confirm(order)
    return sales.ship(order)


@pytest.fixture
def accountant(make_client):
    return make_client(Role.ACCOUNTANT)


def test_chart_of_accounts_created_by_migration(db):
    assert set(Account.objects.values_list("code", flat=True)) >= {C.RAW_MATERIALS, C.REVENUE, C.PRODUCTION}


def test_receipt_posting(world):
    entry = JournalEntry.objects.get(source_type="receipt", source_id=world["receipt"].pk)
    posting = entry.postings.get()
    assert (posting.debit.code, posting.credit.code, posting.amount, posting.supplier) == (
        C.RAW_MATERIALS, C.PAYABLES, 30000, world["supplier"])


def test_production_moves_cost_through_wip(world):
    produce(world["ginger"], 100)  # 10 кг муки × 300 = 3000
    assert balance(C.RAW_MATERIALS) == 30000 - 3000
    assert balance(C.PRODUCTION) == 0  # НЗП закрыт выпуском
    assert balance(C.FINISHED_GOODS) == 3000


def test_wip_while_task_in_progress(world):
    task = production.create_task(world["ginger"], D(50), TODAY)
    production.start(task)
    assert balance(C.PRODUCTION) == 1500


def test_full_defect_goes_to_losses(world):
    produce(world["ginger"], 10, actual=0, defect=10)
    assert balance(C.OTHER_EXPENSES) == 300 and balance(C.PRODUCTION) == 0


def test_shipment_revenue_cost_and_invoice(world):
    produce(world["ginger"], 100)  # себестоимость 30 за шт
    shipment = ship(world["client"], world["ginger"], 40, price=100)
    assert balance(C.RECEIVABLES, client=world["client"]) == 4000
    assert balance(C.REVENUE) == -4000  # кредитовое сальдо дохода
    assert balance(C.COST_OF_SALES) == 1200
    invoice = Invoice.objects.get(shipment=shipment)
    assert (invoice.amount, invoice.due_date) == (4000, TODAY + timedelta(days=10))


def test_write_off_posting(world):
    lot = world["flour"].lots.get()
    stock.write_off(lot, D(2), reason="порча")
    assert balance(C.OTHER_EXPENSES) == 600


def test_trial_balance_is_balanced_and_pnl(world):
    produce(world["ginger"], 100)
    ship(world["client"], world["ginger"], 40)
    stock.write_off(world["flour"].lots.get(), D(1), reason="порча")
    tb = reports.trial_balance(TODAY.replace(day=1), TODAY)
    totals = tb["totals"]
    assert totals["turnover_debit"] == totals["turnover_credit"]
    assert totals["closing_debit"] == totals["closing_credit"]
    pnl = reports.profit_and_loss(TODAY.replace(day=1), TODAY)
    assert (pnl["revenue"], pnl["cost_of_sales"], pnl["other_expenses"], pnl["net_profit"]) == (4000, 1200, 300, 2500)


# --- Платежи и разнесение ------------------------------------------------------


def test_incoming_payment_fifo_and_explicit_invoice(accountant, world):
    produce(world["ginger"], 100)
    first = ship(world["client"], world["ginger"], 10).invoice   # 1000
    second = ship(world["client"], world["ginger"], 20).invoice  # 2000

    # явно в оплату второго счёта, остаток — на первый (FIFO)
    r = accountant.post(PAYMENTS, {"direction": "incoming", "client": world["client"].pk, "invoice": second.pk,
                                   "amount": "2500", "date": str(TODAY)}, format="json")
    assert r.status_code == 201, r.data
    assert {a["invoice_number"]: D(a["amount"]) for a in r.data["allocations"]} == {second.number: 2000, first.number: 500}
    assert balance(C.BANK) == 2500 and balance(C.RECEIVABLES, client=world["client"]) == 500

    invoices = {i["number"]: i for i in accountant.get("/api/accounting/invoices/").data["results"]}
    assert invoices[second.number]["status"] == "paid" and invoices[first.number]["status"] == "partial"


def test_advance_closes_next_invoice(accountant, world):
    accountant.post(PAYMENTS, {"direction": "incoming", "client": world["client"].pk, "amount": "1500",
                               "date": str(TODAY), "method": "cash"}, format="json")
    receivable = reports.receivables()["rows"][0]
    assert receivable["advance"] == 1500 and balance(C.CASH) == 1500

    produce(world["ginger"], 100)
    invoice = ship(world["client"], world["ginger"], 10).invoice  # 1000 — закрывается авансом
    assert sum(a.amount for a in invoice.allocations.all()) == 1000
    assert reports.receivables()["rows"][0]["advance"] == 500


def test_outgoing_payment_reduces_payables(accountant, world):
    r = accountant.post(PAYMENTS, {"direction": "outgoing", "supplier": world["supplier"].pk, "amount": "10000",
                                   "date": str(TODAY)}, format="json")
    assert r.status_code == 201
    row = reports.payables()["rows"][0]
    assert (row["received"], row["paid"], row["debt"]) == (30000, 10000, 20000)


def test_payment_validation(accountant, world):
    base = {"amount": "1", "date": str(TODAY)}
    assert accountant.post(PAYMENTS, {**base, "direction": "incoming"}, format="json").status_code == 400
    assert accountant.post(PAYMENTS, {**base, "direction": "outgoing"}, format="json").status_code == 400
    future = {**base, "direction": "outgoing", "supplier": world["supplier"].pk, "date": str(TODAY + timedelta(days=1))}
    assert accountant.post(PAYMENTS, future, format="json").status_code == 400
    other = Client.objects.create(name="Другой", kind="store")
    produce(world["ginger"], 10)
    invoice = ship(world["client"], world["ginger"], 5).invoice
    wrong = {**base, "direction": "incoming", "client": other.pk, "invoice": invoice.pk}
    assert accountant.post(PAYMENTS, wrong, format="json").status_code == 400


# --- Ручные операции, права, целостность ---------------------------------------


def test_manual_entry_and_auto_entry_protection(accountant, world):
    bank, equity = Account.objects.get(code=C.BANK), Account.objects.get(code=C.RETAINED_EARNINGS)
    r = accountant.post("/api/accounting/entries/", {
        "date": str(TODAY), "description": "Взнос учредителя",
        "postings": [{"debit": bank.pk, "credit": equity.pk, "amount": "500000"}],
    }, format="json")
    assert r.status_code == 201 and r.data["source_type"] == "manual"
    assert balance(C.BANK) == 500000
    assert accountant.delete(f"/api/accounting/entries/{r.data['id']}/").status_code == 204

    auto = JournalEntry.objects.get(source_type="receipt")
    assert accountant.delete(f"/api/accounting/entries/{auto.pk}/").status_code == 400


def test_permissions(make_client, world):
    sales_api = make_client(Role.SALES)
    assert sales_api.get("/api/accounting/invoices/").status_code == 200
    assert sales_api.get("/api/accounting/reports/receivables/").status_code == 200
    assert sales_api.get("/api/accounting/entries/").status_code == 403
    assert sales_api.get("/api/accounting/reports/trial-balance/").status_code == 403
    payload = {"direction": "incoming", "client": world["client"].pk, "amount": "1", "date": str(TODAY)}
    assert sales_api.post(PAYMENTS, payload, format="json").status_code == 403
    assert make_client(Role.STOREKEEPER).get("/api/accounting/invoices/").status_code == 403


def test_failed_posting_rolls_back_business_operation(make_client, world):
    """Проводка в той же транзакции, что и операция: нет счёта выручки — нет и отгрузки."""
    produce(world["ginger"], 10)
    Account.objects.filter(code=C.REVENUE).delete()
    order = SalesOrder.objects.create(client=world["client"], delivery_date=TODAY)
    SalesOrderLine.objects.create(order=order, item=world["ginger"], quantity=5, price=100)
    sales.confirm(order)
    r = make_client(Role.STOREKEEPER).post(f"/api/sales/orders/{order.pk}/ship/")
    assert r.status_code == 400 and "6010" in r.data["detail"]
    assert not Shipment.objects.exists() and SalesOrder.objects.get(pk=order.pk).status == "ready"
    assert stock.available_qty(world["ginger"]) == 10


def test_backfill_is_idempotent(world):
    JournalEntry.objects.all().delete()
    call_command("accounting_backfill")
    count = JournalEntry.objects.count()
    call_command("accounting_backfill")
    assert count == JournalEntry.objects.count() == 1  # одна приёмка


def test_protected_delete_returns_400(make_client, world):
    r = make_client(Role.TECHNOLOGIST).delete(f"/api/catalog/items/{world['flour'].pk}/")
    assert r.status_code == 400 and "используется" in r.data["detail"]


def test_report_endpoints(accountant, world):
    flour_account = Account.objects.get(code=C.RAW_MATERIALS)
    card = accountant.get(f"/api/accounting/reports/account-card/?account={flour_account.pk}").data
    assert card["rows"][0]["corr_account"] == C.PAYABLES and card["closing"] == 30000
    assert accountant.get("/api/accounting/reports/profit-loss/?date_from=2026-02-01&date_to=2026-01-01").status_code == 400
    assert accountant.get("/api/accounting/reports/payables/").data["total_debt"] == 30000
