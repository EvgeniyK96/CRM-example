from rest_framework import serializers

from .models import Category, Item, ItemKind, Supplier, Unit


class UnitSerializer(serializers.ModelSerializer):
    class Meta:
        model = Unit
        fields = "__all__"


class CategorySerializer(serializers.ModelSerializer):
    kind_display = serializers.CharField(source="get_kind_display", read_only=True)

    class Meta:
        model = Category
        fields = "__all__"


class ItemSerializer(serializers.ModelSerializer):
    kind_display = serializers.CharField(source="get_kind_display", read_only=True)
    unit_code = serializers.CharField(source="unit.code", read_only=True)
    category_name = serializers.CharField(source="category.name", read_only=True, default=None)
    department_name = serializers.CharField(source="department.name", read_only=True, default=None)

    class Meta:
        model = Item
        fields = "__all__"

    def validate(self, attrs):
        def get(field):
            return attrs.get(field, getattr(self.instance, field, None))

        kind, category, department = get("kind"), get("category"), get("department")
        errors = {}
        if category and category.kind != kind:
            errors["category"] = "Категория относится к другому типу номенклатуры."
        if kind == ItemKind.PRODUCT and not department:
            errors["department"] = "Для готовой продукции укажите цех-изготовитель."
        if kind == ItemKind.RAW and department:
            errors["department"] = "У сырья не бывает цеха-изготовителя."
        if department and not department.is_production:
            errors["department"] = "Подразделение не является производственным цехом."
        if errors:
            raise serializers.ValidationError(errors)
        return attrs


class SupplierSerializer(serializers.ModelSerializer):
    class Meta:
        model = Supplier
        fields = "__all__"
