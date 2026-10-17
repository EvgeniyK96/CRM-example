from decimal import Decimal

from django.db.models import Sum
from django.utils import timezone
from rest_framework import serializers

from core.serializers import positive

from . import services
from .models import ProductionTask, TaskAllocation, TaskConsumption


class TaskAllocationSerializer(serializers.ModelSerializer):
    order = serializers.IntegerField(source="order_line.order_id", read_only=True)
    order_number = serializers.CharField(source="order_line.order.number", read_only=True)
    order_status = serializers.CharField(source="order_line.order.status", read_only=True)
    client_name = serializers.CharField(source="order_line.order.client.name", read_only=True)
    delivery_date = serializers.DateField(source="order_line.order.delivery_date", read_only=True)

    class Meta:
        model = TaskAllocation
        fields = ("id", "order", "order_number", "order_status", "client_name", "delivery_date", "quantity", "fulfilled")


class TaskConsumptionSerializer(serializers.ModelSerializer):
    lot = serializers.IntegerField(source="move.lot_id", read_only=True)
    lot_number = serializers.CharField(source="move.lot.number", read_only=True)
    item_name = serializers.CharField(source="move.lot.item.name", read_only=True)
    unit_code = serializers.CharField(source="move.lot.item.unit.code", read_only=True)
    supplier_name = serializers.CharField(source="move.lot.supplier.name", read_only=True, default=None)
    expiry_date = serializers.DateField(source="move.lot.expiry_date", read_only=True)
    unit_cost = serializers.DecimalField(source="move.lot.unit_cost", max_digits=12, decimal_places=2, read_only=True)
    quantity = serializers.SerializerMethodField()

    class Meta:
        model = TaskConsumption
        fields = ("id", "lot", "lot_number", "item_name", "unit_code", "supplier_name", "expiry_date", "unit_cost", "quantity")

    def get_quantity(self, c):
        return f"{-c.move.quantity:.3f}"


class ProductionTaskSerializer(serializers.ModelSerializer):
    department_name = serializers.CharField(source="department.name", read_only=True)
    product_name = serializers.CharField(source="product.name", read_only=True)
    unit_code = serializers.CharField(source="product.unit.code", read_only=True)
    recipe_version = serializers.IntegerField(source="recipe.version", read_only=True)
    status_display = serializers.CharField(source="get_status_display", read_only=True)
    output_lot_number = serializers.CharField(source="output_lot.number", read_only=True, default=None)
    unit_cost = serializers.DecimalField(
        source="output_lot.unit_cost", max_digits=12, decimal_places=2, read_only=True, default=None
    )
    allocations = TaskAllocationSerializer(many=True, read_only=True)
    created_by_name = serializers.CharField(source="created_by.username", read_only=True, default=None)
    started_by_name = serializers.CharField(source="started_by.username", read_only=True, default=None)
    finished_by_name = serializers.CharField(source="finished_by.username", read_only=True, default=None)

    class Meta:
        model = ProductionTask
        fields = (
            "id", "number", "department", "department_name", "product", "product_name", "unit_code", "recipe",
            "recipe_version", "planned_qty", "planned_date", "status", "status_display", "actual_qty", "defect_qty",
            "raw_cost", "unit_cost", "output_lot", "output_lot_number", "comment", "allocations",
            "created_by_name", "created_at", "started_by_name", "started_at", "finished_by_name", "finished_at",
        )
        read_only_fields = (
            "department", "recipe", "status", "actual_qty", "defect_qty", "raw_cost", "output_lot", "started_at",
            "finished_at",
        )

    def validate_product(self, value):
        if self.instance and value != self.instance.product:
            raise serializers.ValidationError("Продукт задания менять нельзя — создайте новое задание.")
        services.check_product(value)
        services.active_recipe(value)
        return value

    def validate_planned_qty(self, value):
        positive(value)
        if self.instance:
            allocated = self.instance.allocations.aggregate(s=Sum("quantity"))["s"] or Decimal(0)
            if value < allocated:
                raise serializers.ValidationError(f"По заказам распределено {allocated.normalize():f} — план не может быть меньше.")
        return value

    def validate_planned_date(self, value):
        if value < timezone.localdate():
            raise serializers.ValidationError("Плановая дата не может быть в прошлом.")
        return value

    def validate(self, attrs):
        if self.instance and not self.instance.is_editable:
            raise serializers.ValidationError("Изменять можно только запланированное задание.")
        return attrs

    def create(self, validated_data):
        return services.create_task(
            validated_data["product"], validated_data["planned_qty"], validated_data["planned_date"],
            user=validated_data.get("created_by"), comment=validated_data.get("comment", ""),
        )


class FinishSerializer(serializers.Serializer):
    actual_qty = serializers.DecimalField(max_digits=12, decimal_places=3, min_value=Decimal(0))
    defect_qty = serializers.DecimalField(max_digits=12, decimal_places=3, min_value=Decimal(0), default=Decimal(0))
    comment = serializers.CharField(required=False, allow_blank=True, default="")
