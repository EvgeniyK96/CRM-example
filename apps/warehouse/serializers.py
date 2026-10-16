from decimal import Decimal

from rest_framework import serializers

from apps.catalog.models import Item

from .models import Lot, StockMove
from .services import expiry_status


class LotSerializer(serializers.ModelSerializer):
    item_code = serializers.CharField(source="item.code", read_only=True)
    item_name = serializers.CharField(source="item.name", read_only=True)
    item_kind = serializers.CharField(source="item.kind", read_only=True)
    unit_code = serializers.CharField(source="item.unit.code", read_only=True)
    supplier_name = serializers.CharField(source="supplier.name", read_only=True, default=None)
    balance = serializers.DecimalField(max_digits=14, decimal_places=3, read_only=True)

    class Meta:
        model = Lot
        fields = (
            "id", "number", "item", "item_code", "item_name", "item_kind", "unit_code", "supplier", "supplier_name",
            "date", "expiry_date", "unit_cost", "balance",
        )

    def to_representation(self, lot):
        data = super().to_representation(lot)
        data["expiry_status"], data["days_left"] = expiry_status(lot)
        return data


class StockSerializer(serializers.ModelSerializer):
    """Сводный остаток по номенклатуре."""

    unit_code = serializers.CharField(source="unit.code", read_only=True)
    balance = serializers.DecimalField(max_digits=14, decimal_places=3, read_only=True)
    available = serializers.DecimalField(max_digits=14, decimal_places=3, read_only=True)
    expired = serializers.DecimalField(max_digits=14, decimal_places=3, read_only=True)
    below_min = serializers.BooleanField(read_only=True)
    nearest_expiry = serializers.DateField(read_only=True)

    class Meta:
        model = Item
        fields = (
            "id", "code", "name", "kind", "unit_code", "min_stock", "balance", "available", "expired", "below_min",
            "nearest_expiry",
        )


class StockMoveSerializer(serializers.ModelSerializer):
    lot_number = serializers.CharField(source="lot.number", read_only=True)
    item = serializers.IntegerField(source="lot.item_id", read_only=True)
    item_name = serializers.CharField(source="lot.item.name", read_only=True)
    unit_code = serializers.CharField(source="lot.item.unit.code", read_only=True)
    kind_display = serializers.CharField(source="get_kind_display", read_only=True)
    created_by_name = serializers.CharField(source="created_by.username", read_only=True, default=None)

    class Meta:
        model = StockMove
        fields = (
            "id", "lot", "lot_number", "item", "item_name", "unit_code", "kind", "kind_display", "quantity",
            "reference", "created_by_name", "created_at",
        )


class WriteOffSerializer(serializers.Serializer):
    quantity = serializers.DecimalField(max_digits=12, decimal_places=3, min_value=Decimal("0.001"))
    reason = serializers.CharField(max_length=200)
