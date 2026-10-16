from django.contrib import admin

from .models import Category, Item, Supplier, Unit

admin.site.register(Unit)


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ("name", "kind")
    list_filter = ("kind",)


@admin.register(Item)
class ItemAdmin(admin.ModelAdmin):
    list_display = ("code", "name", "kind", "unit", "department", "shelf_life_days", "is_active")
    list_filter = ("kind", "department", "category", "is_active")
    search_fields = ("code", "name")


@admin.register(Supplier)
class SupplierAdmin(admin.ModelAdmin):
    list_display = ("name", "tax_id", "contact_person", "phone", "is_active")
    search_fields = ("name", "tax_id")
