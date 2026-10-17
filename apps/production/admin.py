from django.contrib import admin

from .models import ProductionTask, TaskAllocation, TaskConsumption


class TaskAllocationInline(admin.TabularInline):
    model = TaskAllocation
    extra = 0


class TaskConsumptionInline(admin.TabularInline):
    model = TaskConsumption
    extra = 0
    can_delete = False
    readonly_fields = ("move",)


@admin.register(ProductionTask)
class ProductionTaskAdmin(admin.ModelAdmin):
    list_display = ("number", "department", "product", "planned_qty", "planned_date", "status", "actual_qty", "defect_qty")
    list_filter = ("status", "department")
    search_fields = ("number", "product__name")
    inlines = [TaskAllocationInline, TaskConsumptionInline]
