from django.contrib import admin

from .models import PayrollPeriod, PayrollRate, Payslip, PayslipLine


@admin.register(PayrollRate)
class PayrollRateAdmin(admin.ModelAdmin):
    list_display = ("code", "name", "payer", "base", "percent", "account_code", "is_active")


class PayslipLineInline(admin.TabularInline):
    model = PayslipLine
    extra = 0


@admin.register(Payslip)
class PayslipAdmin(admin.ModelAdmin):
    list_display = ("period", "employee", "gross", "withheld", "net")
    list_filter = ("period",)
    inlines = [PayslipLineInline]


admin.site.register(PayrollPeriod)
