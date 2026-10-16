from django.contrib import admin

from .models import Client, SalesOrder, SalesOrderLine


@admin.register(Client)
class ClientAdmin(admin.ModelAdmin):
    list_display = ("name", "kind", "phone", "discount_percent", "payment_delay_days", "is_active")
    list_filter = ("kind", "is_active")
    search_fields = ("name", "tax_id")


class SalesOrderLineInline(admin.TabularInline):
    model = SalesOrderLine
    extra = 0
    readonly_fields = ("reserved_qty", "to_produce")


@admin.register(SalesOrder)
class SalesOrderAdmin(admin.ModelAdmin):
    list_display = ("number", "client", "status", "delivery_date", "created_by", "created_at")
    list_filter = ("status", "client__kind")
    search_fields = ("number", "client__name")
    inlines = [SalesOrderLineInline]
