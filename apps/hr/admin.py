from django.contrib import admin

from .models import Absence, Department, Employee, Holiday, HROrder, Position

admin.site.register(Department)
admin.site.register(Position)


@admin.register(Employee)
class EmployeeAdmin(admin.ModelAdmin):
    list_display = ("full_name", "department", "position", "status", "hire_date")
    list_filter = ("department", "status")
    search_fields = ("last_name", "first_name", "tax_id")


@admin.register(HROrder)
class HROrderAdmin(admin.ModelAdmin):
    list_display = ("number", "kind", "employee", "date", "to_department", "to_position", "to_salary")
    list_filter = ("kind",)


@admin.register(Absence)
class AbsenceAdmin(admin.ModelAdmin):
    list_display = ("employee", "kind", "date_from", "date_to")
    list_filter = ("kind",)


admin.site.register(Holiday)
