from decimal import Decimal

from django.db import transaction
from rest_framework import serializers

from apps.catalog.models import ItemKind

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
        if value <= 0:
            raise serializers.ValidationError("Количество должно быть больше нуля.")
        return value

    def validate_loss_percent(self, value):
        if not 0 <= value < 100:
            raise serializers.ValidationError("Потери должны быть от 0 до 100%.")
        return value


class RecipeSerializer(serializers.ModelSerializer):
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
        if value <= 0:
            raise serializers.ValidationError("Выход партии должен быть больше нуля.")
        return value

    def validate_lines(self, lines):
        ids = [line["ingredient"].pk for line in lines]
        if len(ids) != len(set(ids)):
            raise serializers.ValidationError("Сырьё в рецептуре не должно повторяться.")
        return lines

    def validate(self, attrs):
        if self.instance and not self.instance.is_editable:
            raise serializers.ValidationError("Изменять можно только черновик. Создайте новую версию.")
        return attrs

    @transaction.atomic
    def create(self, validated_data):
        lines = validated_data.pop("lines", [])
        validated_data["version"] = next_version(validated_data["product"])
        recipe = Recipe.objects.create(**validated_data)
        self._save_lines(recipe, lines)
        return recipe

    @transaction.atomic
    def update(self, instance, validated_data):
        lines = validated_data.pop("lines", None)
        instance = super().update(instance, validated_data)
        if lines is not None:
            instance.lines.all().delete()
            self._save_lines(instance, lines)
        return instance

    @staticmethod
    def _save_lines(recipe, lines):
        RecipeLine.objects.bulk_create(RecipeLine(recipe=recipe, **line) for line in lines)


class CalculateSerializer(serializers.Serializer):
    qty = serializers.DecimalField(max_digits=12, decimal_places=3, min_value=Decimal("0.001"))
