"""
Глобальный поиск из шапки: номера документов, клиенты, номенклатура, партии, сотрудники.
Каждая группа видна только ролям, которым доступен соответствующий раздел (как в меню).
"""

from django.db.models import Q

from apps.accounting.models import Invoice
from apps.accounts.models import Role
from apps.catalog.models import Item
from apps.hr.models import Employee
from apps.production.models import ProductionTask
from apps.purchasing.models import PurchaseOrder, Receipt
from apps.recipes.models import Recipe
from apps.sales.models import Client, SalesOrder, Shipment
from apps.warehouse.models import Lot

ALL = "all"
LIMIT = 5


def _orders(q):
    for o in SalesOrder.objects.filter(Q(number__icontains=q) | Q(client__name__icontains=q)).select_related("client")[:LIMIT]:
        yield o.number, f"{o.client.name} · {o.get_status_display()}", f"/orders/{o.pk}"


def _clients(q):
    for c in Client.objects.filter(Q(name__icontains=q) | Q(tax_id__icontains=q) | Q(phone__icontains=q))[:LIMIT]:
        yield c.name, c.get_kind_display(), f"/clients?q={c.name}"


def _items(q):
    for i in Item.objects.filter(Q(name__icontains=q) | Q(code__icontains=q))[:LIMIT]:
        yield i.name, f"{i.code} · {i.get_kind_display()}", f"/items?q={i.code}&kind={i.kind}"


def _recipes(q):
    for r in Recipe.objects.filter(product__name__icontains=q, status=Recipe.Status.ACTIVE).select_related("product")[:LIMIT]:
        yield r.product.name, f"Рецептура, версия {r.version}", f"/recipes/{r.pk}"


def _tasks(q):
    tasks = ProductionTask.objects.filter(Q(number__icontains=q) | Q(product__name__icontains=q)).select_related("product")
    for t in tasks.order_by("-pk")[:LIMIT]:
        yield t.number, f"{t.product.name} · {t.get_status_display()}", f"/tasks/{t.pk}"


def _lots(q):
    for lot in Lot.objects.filter(number__icontains=q).select_related("item")[:LIMIT]:
        yield lot.number, f"{lot.item.name}, годна до {lot.expiry_date:%d.%m.%Y}", f"/trace/{lot.pk}"


def _shipments(q):
    shipments = Shipment.objects.filter(Q(number__icontains=q) | Q(order__client__name__icontains=q)).select_related("order__client")
    for s in shipments.order_by("-pk")[:LIMIT]:
        yield s.number, f"{s.order.client.name}, {s.date:%d.%m.%Y}", f"/shipments/{s.pk}"


def _invoices(q):
    invoices = Invoice.objects.filter(Q(number__icontains=q) | Q(client__name__icontains=q)).select_related("client")
    for i in invoices.order_by("-pk")[:LIMIT]:
        yield i.number, f"{i.client.name}, {i.amount:.2f} ₸", f"/invoices?q={i.number}"


def _purchase_orders(q):
    orders = PurchaseOrder.objects.filter(Q(number__icontains=q) | Q(supplier__name__icontains=q)).select_related("supplier")
    for o in orders.order_by("-pk")[:LIMIT]:
        yield o.number, f"{o.supplier.name} · {o.get_status_display()}", f"/purchase-orders/{o.pk}"


def _receipts(q):
    receipts = Receipt.objects.filter(Q(number__icontains=q) | Q(invoice_number__icontains=q)).select_related("supplier")
    for r in receipts.order_by("-pk")[:LIMIT]:
        yield r.number, f"{r.supplier.name}, {r.date:%d.%m.%Y}", f"/receipts/{r.pk}"


def _employees(q):
    employees = Employee.objects.filter(Q(last_name__icontains=q) | Q(first_name__icontains=q) | Q(tax_id__icontains=q))
    for e in employees.select_related("department")[:LIMIT]:
        yield e.full_name, e.department.name, f"/employees?q={e.last_name}"


# тип, подпись группы, роли (как у разделов меню), поиск
GROUPS = [
    ("order", "Заказы клиентов", (Role.SALES, Role.ACCOUNTANT, Role.STOREKEEPER, Role.SHOP_HEAD), _orders),
    ("client", "Клиенты", (Role.SALES, Role.ACCOUNTANT), _clients),
    ("task", "Производственные задания",
     (Role.SHOP_HEAD, Role.TECHNOLOGIST, Role.STOREKEEPER, Role.ACCOUNTANT, Role.SALES), _tasks),
    ("item", "Номенклатура", ALL, _items),
    ("recipe", "Рецептуры", (Role.TECHNOLOGIST, Role.SHOP_HEAD, Role.ACCOUNTANT), _recipes),
    ("lot", "Партии", ALL, _lots),
    ("shipment", "Отгрузки", (Role.STOREKEEPER, Role.SALES, Role.ACCOUNTANT), _shipments),
    ("invoice", "Счета покупателям", (Role.ACCOUNTANT, Role.SALES), _invoices),
    ("purchase_order", "Заявки поставщикам", (Role.STOREKEEPER, Role.ACCOUNTANT), _purchase_orders),
    ("receipt", "Приёмки", (Role.STOREKEEPER, Role.ACCOUNTANT), _receipts),
    ("employee", "Сотрудники", (Role.HR, Role.ACCOUNTANT, Role.SHOP_HEAD), _employees),
]


def search(user, q: str) -> list[dict]:
    q = q.strip()
    if len(q) < 2:
        return []
    groups = []
    for kind, label, roles, find in GROUPS:
        if roles != ALL and user.role != Role.ADMIN and user.role not in roles:
            continue
        results = [{"title": title, "subtitle": subtitle, "path": path} for title, subtitle, path in find(q)]
        if results:
            groups.append({"type": kind, "label": label, "results": results})
    return groups
