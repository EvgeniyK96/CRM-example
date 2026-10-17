from django.db import transaction
from rest_framework import serializers

from core.serializers import positive

from . import services
from .models import Absence, Department, Employee, Holiday, HROrder, Position


class DepartmentSerializer(serializers.ModelSerializer):
    class Meta:
        model = Department
        fields = "__all__"


class PositionSerializer(serializers.ModelSerializer):
    class Meta:
        model = Position
        fields = "__all__"


class EmployeeSerializer(serializers.ModelSerializer):
    full_name = serializers.CharField(read_only=True)
    department_name = serializers.CharField(source="department.name", read_only=True)
    position_name = serializers.CharField(source="position.name", read_only=True)
    username = serializers.CharField(source="user.username", read_only=True, default=None)

    # Эти поля после приёма меняются только кадровым приказом
    ORDER_FIELDS = ("department", "position", "salary", "status", "fire_date", "hire_date")

    class Meta:
        model = Employee
        fields = "__all__"
        extra_kwargs = {"salary": {"required": False}}

    def validate(self, attrs):
        if self.instance:
            changed = [f for f in self.ORDER_FIELDS if f in attrs and attrs[f] != getattr(self.instance, f)]
            if changed:
                raise serializers.ValidationError(
                    {f: "Изменяется кадровым приказом (перевод, оклад, увольнение)." for f in changed}
                )
        hire = attrs.get("hire_date", getattr(self.instance, "hire_date", None))
        fire = attrs.get("fire_date", getattr(self.instance, "fire_date", None))
        if hire and fire and fire < hire:
            raise serializers.ValidationError({"fire_date": "Дата увольнения раньше даты приёма."})
        return attrs

    @transaction.atomic
    def create(self, validated_data):
        employee = super().create(validated_data)
        services.hire(employee, self.context["request"].user if "request" in self.context else None)
        return employee


class HROrderSerializer(serializers.ModelSerializer):
    kind_display = serializers.CharField(source="get_kind_display", read_only=True)
    employee_name = serializers.CharField(source="employee.full_name", read_only=True)
    from_department_name = serializers.CharField(source="from_department.name", read_only=True, default=None)
    to_department_name = serializers.CharField(source="to_department.name", read_only=True, default=None)
    from_position_name = serializers.CharField(source="from_position.name", read_only=True, default=None)
    to_position_name = serializers.CharField(source="to_position.name", read_only=True, default=None)
    created_by_name = serializers.CharField(source="created_by.username", read_only=True, default=None)

    class Meta:
        model = HROrder
        fields = (
            "id", "number", "kind", "kind_display", "employee", "employee_name", "date", "from_department",
            "from_department_name", "to_department", "to_department_name", "from_position", "from_position_name",
            "to_position", "to_position_name", "from_salary", "to_salary", "reason", "created_by_name", "created_at",
        )
        read_only_fields = ("from_department", "from_position", "from_salary")

    def validate_kind(self, value):
        if value == HROrder.Kind.HIRE:
            raise serializers.ValidationError("Приём оформляется созданием карточки сотрудника.")
        return value

    def validate_to_salary(self, value):
        return positive(value, "Оклад должен быть больше нуля.")

    def create(self, validated_data):
        return services.issue_order(
            validated_data["employee"], validated_data["kind"], validated_data["date"],
            department=validated_data.get("to_department"), position=validated_data.get("to_position"),
            salary=validated_data.get("to_salary"), reason=validated_data.get("reason", ""),
            user=validated_data.get("created_by"),
        )


class AbsenceSerializer(serializers.ModelSerializer):
    kind_display = serializers.CharField(source="get_kind_display", read_only=True)
    employee_name = serializers.CharField(source="employee.full_name", read_only=True)
    department_name = serializers.CharField(source="employee.department.name", read_only=True)
    days = serializers.SerializerMethodField()

    class Meta:
        model = Absence
        fields = ("id", "employee", "employee_name", "department_name", "kind", "kind_display", "date_from", "date_to",
                  "days", "comment")

    def get_days(self, absence):
        return (absence.date_to - absence.date_from).days + 1

    def validate(self, attrs):
        def get(f):
            return attrs.get(f, getattr(self.instance, f, None))

        services.check_absence(get("employee"), get("date_from"), get("date_to"),
                               exclude_pk=self.instance.pk if self.instance else None)
        return attrs


class HolidaySerializer(serializers.ModelSerializer):
    class Meta:
        model = Holiday
        fields = "__all__"
