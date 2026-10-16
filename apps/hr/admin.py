from django.contrib import admin

from .models import Department, Employee, Position

admin.site.register(Department)
admin.site.register(Position)


@admin.register(Employee)
class EmployeeAdmin(admin.ModelAdmin):
    list_display = ("full_name", "department", "position", "status", "hire_date")
    list_filter = ("department", "status")
    search_fields = ("last_name", "first_name", "tax_id")
