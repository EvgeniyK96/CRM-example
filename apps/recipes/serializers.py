from decimal import Decimal

from django.db import transaction
from rest_framework import serializers

from apps.catalog.models import ItemKind
from core.serializers import LinesWriteMixin, positive

from .models import Recipe, RecipeLine
from .services import next_version


class RecipeLineSerializer(serializers.ModelSerializer):
    ingredient_name = serializers.CharField(source="ingredient.name", read_only=True)
    unit_code = serializers.CharField(source="ingredient.unit.code", read_only=True)

    class Meta:
        model = RecipeLine
        fields = ("id", "ingredient", "ingredient_name", "unit_code", "quantity", "loss_percent")

    def validate_ingredient(self, value):
        if value.kind != ItemKind.RAW:
            raise serializers.ValidationError("В рецептуру можно включать только сырьё.")
        return value

    def validate_quantity(self, value):
        return positive(value)

    def validate_loss_percent(self, value):
        if not 0 <= value < 100:
            raise serializers.ValidationError("Потери должны быть от 0 до 100%.")
        return value


class RecipeSerializer(LinesWriteMixin, serializers.ModelSerializer):
    lines_parent_field = "recipe"
    lines_unique_field = "ingredient"
    not_editable_message = "Изменять можно только черновик. Создайте новую версию."

    lines = RecipeLineSerializer(many=True, required=False)
    product_name = serializers.CharField(source="product.name", read_only=True)
    product_unit = serializers.CharField(source="product.unit.code", read_only=True)
    department_name = serializers.CharField(source="product.department.name", read_only=True, default=None)
    status_display = serializers.CharField(source="get_status_display", read_only=True)
    created_by_name = serializers.CharField(source="created_by.username", read_only=True, default=None)

    class Meta:
        model = Recipe
        fields = (
            "id", "product", "product_name", "product_unit", "department_name", "version", "status",
            "status_display", "output_qty", "note", "lines", "created_by_name", "created_at", "activated_at",
        )
        read_only_fields = ("version", "status", "created_at", "activated_at")

    def validate_product(self, value):
        if value.kind != ItemKind.PRODUCT:
            raise serializers.ValidationError("Рецептура составляется только для готовой продукции.")
        if self.instance and value != self.instance.product:
            raise serializers.ValidationError("Нельзя сменить продукт у существующей рецептуры.")
        return value

    def validate_output_qty(self, value):
        return positive(value, "Выход партии должен быть больше нуля.")

    @transaction.atomic
    def create(self, validated_data):
        validated_data["version"] = next_version(validated_data["product"])
        return super().create(validated_data)


class CalculateSerializer(serializers.Serializer):
    qty = serializers.DecimalField(max_digits=12, decimal_places=3, min_value=Decimal("0.001"))
