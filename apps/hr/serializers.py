from rest_framework import serializers

from .models import Department, Employee, Position


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

    class Meta:
        model = Employee
        fields = "__all__"

    def validate(self, attrs):
        hire = attrs.get("hire_date", getattr(self.instance, "hire_date", None))
        fire = attrs.get("fire_date", getattr(self.instance, "fire_date", None))
        if hire and fire and fire < hire:
            raise serializers.ValidationError({"fire_date": "Дата увольнения раньше даты приёма."})
        return attrs
