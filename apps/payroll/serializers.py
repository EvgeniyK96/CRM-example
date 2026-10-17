from django.utils import timezone
from rest_framework import serializers

from .models import PayrollPeriod, PayrollRate, Payslip, PayslipLine


class PayrollRateSerializer(serializers.ModelSerializer):
    payer_display = serializers.CharField(source="get_payer_display", read_only=True)
    base_display = serializers.CharField(source="get_base_display", read_only=True)

    class Meta:
        model = PayrollRate
        fields = "__all__"


class PayslipLineSerializer(serializers.ModelSerializer):
    code = serializers.CharField(source="rate.code", read_only=True)
    name = serializers.CharField(source="rate.name", read_only=True)

    class Meta:
        model = PayslipLine
        fields = ("id", "code", "name", "payer", "base", "percent", "amount")


class PayslipSerializer(serializers.ModelSerializer):
    employee_name = serializers.CharField(source="employee.full_name", read_only=True)
    department_name = serializers.CharField(source="department.name", read_only=True)
    position_name = serializers.CharField(source="position.name", read_only=True)
    period_label = serializers.CharField(source="period.__str__", read_only=True)
    period_status = serializers.CharField(source="period.status", read_only=True)
    lines = PayslipLineSerializer(many=True, read_only=True)

    class Meta:
        model = Payslip
        fields = (
            "id", "period", "period_label", "period_status", "employee", "employee_name", "department",
            "department_name", "position_name", "salary", "norm_days", "worked_days", "vacation_days", "sick_days",
            "unpaid_days", "salary_accrued", "vacation_pay", "sick_pay", "bonus", "gross", "withheld", "net",
            "employer_total", "lines",
        )
        read_only_fields = tuple(f for f in fields if f != "bonus")


class PayrollPeriodSerializer(serializers.ModelSerializer):
    status_display = serializers.CharField(source="get_status_display", read_only=True)
    totals = serializers.SerializerMethodField()

    class Meta:
        model = PayrollPeriod
        fields = ("id", "year", "month", "status", "status_display", "calculated_at", "posted_at", "paid_at", "totals")
        read_only_fields = ("status", "calculated_at", "posted_at", "paid_at")

    def get_totals(self, period):
        payslips = list(period.payslips.all())
        return {
            "employees": len(payslips),
            **{key: f"{sum((getattr(p, key) for p in payslips), 0):.2f}"
               for key in ("gross", "withheld", "net", "employer_total")},
        }

    def validate(self, attrs):
        today = timezone.localdate()
        if (attrs["year"], attrs["month"]) > (today.year, today.month):
            raise serializers.ValidationError("Нельзя рассчитать зарплату за будущий месяц.")
        return attrs


class PayMethodSerializer(serializers.Serializer):
    method = serializers.ChoiceField(choices=[("bank", "Расчётный счёт"), ("cash", "Касса")], default="bank")
