from django.contrib import admin

from .models import PurchaseOrder, PurchaseOrderLine, Receipt, ReceiptLine


class PurchaseOrderLineInline(admin.TabularInline):
    model = PurchaseOrderLine
    extra = 0


@admin.register(PurchaseOrder)
class PurchaseOrderAdmin(admin.ModelAdmin):
    list_display = ("number", "supplier", "status", "expected_date", "created_at")
    list_filter = ("status", "supplier")
    search_fields = ("number",)
    inlines = [PurchaseOrderLineInline]


class ReceiptLineInline(admin.TabularInline):
    model = ReceiptLine
    extra = 0
    readonly_fields = ("lot",)


@admin.register(Receipt)
class ReceiptAdmin(admin.ModelAdmin):
    list_display = ("number", "supplier", "date", "status", "order")
    list_filter = ("status", "supplier")
    search_fields = ("number", "invoice_number")
    inlines = [ReceiptLineInline]
