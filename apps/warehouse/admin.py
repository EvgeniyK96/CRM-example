from django.contrib import admin

from .models import Lot, StockMove


class StockMoveInline(admin.TabularInline):
    model = StockMove
    extra = 0
    can_delete = False
    readonly_fields = ("kind", "quantity", "reference", "created_by", "created_at")


@admin.register(Lot)
class LotAdmin(admin.ModelAdmin):
    list_display = ("number", "item", "supplier", "date", "expiry_date", "unit_cost")
    list_filter = ("item__kind", "supplier")
    search_fields = ("number", "item__name")
    inlines = [StockMoveInline]


@admin.register(StockMove)
class StockMoveAdmin(admin.ModelAdmin):
    list_display = ("created_at", "lot", "kind", "quantity", "reference", "created_by")
    list_filter = ("kind",)

    def has_change_permission(self, request, obj=None):
        return False
