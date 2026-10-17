from rest_framework import serializers

from .models import User


class UserSerializer(serializers.ModelSerializer):
    role_display = serializers.CharField(source="get_role_display", read_only=True)
    # Подразделение — из карточки сотрудника (у начальника цеха ограничивает доступ к заданиям)
    department = serializers.SerializerMethodField()
    department_name = serializers.SerializerMethodField()
    production_department = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = (
            "id", "username", "first_name", "last_name", "email", "role", "role_display", "is_active", "department",
            "department_name", "production_department",
        )
        read_only_fields = ("role", "is_active")

    def _employee(self, user):
        return getattr(user, "employee", None)  # нет карточки сотрудника — None

    def get_department(self, user):
        employee = self._employee(user)
        return employee.department_id if employee else None

    def get_department_name(self, user):
        employee = self._employee(user)
        return employee.department.name if employee else None

    def get_production_department(self, user):
        """Производственный цех сотрудника — только он доступен начальнику цеха."""
        employee = self._employee(user)
        return employee.department_id if employee and employee.department.is_production else None


class UserAdminSerializer(serializers.ModelSerializer):
    """Для админа: создание и редактирование пользователей с ролью."""

    password = serializers.CharField(write_only=True, required=False, min_length=8)
    role_display = serializers.CharField(source="get_role_display", read_only=True)

    class Meta:
        model = User
        fields = ("id", "username", "first_name", "last_name", "email", "role", "role_display", "is_active", "password")

    def create(self, validated_data):
        password = validated_data.pop("password", None)
        user = User(**validated_data)
        user.set_password(password) if password else user.set_unusable_password()
        user.save()
        return user

    def update(self, instance, validated_data):
        password = validated_data.pop("password", None)
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        if password:
            instance.set_password(password)
        instance.save()
        return instance
