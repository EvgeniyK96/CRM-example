from django.utils import timezone
from rest_framework import serializers

from apps.catalog.models import ItemKind
from core.serializers import LinesWriteMixin, positive

from .models import Client, SalesOrder, SalesOrderLine
from .services import list_price


def validate_discount(value):
    if not 0 <= value < 100:
        raise serializers.ValidationError("Скидка должна быть от 0 до 100%.")
    return value


class ClientSerializer(serializers.ModelSerializer):
    kind_display = serializers.CharField(source="get_kind_display", read_only=True)

    class Meta:
        model = Client
        fields = "__all__"

    def validate_discount_percent(self, value):
        return validate_discount(value)


class SalesOrderLineSerializer(serializers.ModelSerializer):
    item_name = serializers.CharField(source="item.name", read_only=True)
    unit_code = serializers.CharField(source="item.unit.code", read_only=True)
    # Не указана — подставится цена из прайса с учётом скидки заказа
    price = serializers.DecimalField(max_digits=12, decimal_places=2, required=False, allow_null=True)
    amount = serializers.SerializerMethodField()

    class Meta:
        model = SalesOrderLine
        fields = ("id", "item", "item_name", "unit_code", "quantity", "price", "amount", "reserved_qty", "to_produce")
        read_only_fields = ("reserved_qty", "to_produce")

    def get_amount(self, line):
        return f"{line.amount:.2f}"

    def validate_item(self, value):
        if value.kind != ItemKind.PRODUCT:
            raise serializers.ValidationError("В заказ можно включать только готовую продукцию.")
        if not value.is_active:
            raise serializers.ValidationError("Продукция снята с производства.")
        return value

    def validate_quantity(self, value):
        return positive(value)

    def validate_price(self, value):
        if value is not None and value < 0:
            raise serializers.ValidationError("Цена не может быть отрицательной.")
        return value


class SalesOrderSerializer(LinesWriteMixin, serializers.ModelSerializer):
    lines_parent_field = "order"
    lines_unique_field = "item"
    not_editable_message = "Подтверждённый заказ изменить нельзя. Верните его в работу."

    lines = SalesOrderLineSerializer(many=True, required=False)
    client_name = serializers.CharField(source="client.name", read_only=True)
    client_kind = serializers.CharField(source="client.kind", read_only=True)
    status_display = serializers.CharField(source="get_status_display", read_only=True)
    created_by_name = serializers.CharField(source="created_by.username", read_only=True, default=None)
    confirmed_by_name = serializers.CharField(source="confirmed_by.username", read_only=True, default=None)
    total = serializers.SerializerMethodField()

    class Meta:
        model = SalesOrder
        fields = (
            "id", "number", "client", "client_name", "client_kind", "status", "status_display", "delivery_date",
            "delivery_address", "discount_percent", "comment", "lines", "total", "created_by_name", "created_at",
            "confirmed_by_name", "confirmed_at",
        )
        read_only_fields = ("status", "confirmed_at")

    def get_total(self, order):
        return f"{sum((line.amount for line in order.lines.all()), 0):.2f}"

    def validate_client(self, value):
        if not value.is_active:
            raise serializers.ValidationError("Клиент неактивен.")
        return value

    def validate_discount_percent(self, value):
        return validate_discount(value)

    def validate_delivery_date(self, value):
        if value < timezone.localdate():
            raise serializers.ValidationError("Дата отгрузки не может быть в прошлом.")
        return value

    def create(self, validated_data):
        # Скидка и адрес по умолчанию — из карточки клиента; дальше заказ живёт со своими значениями
        client = validated_data["client"]
        validated_data.setdefault("discount_percent", client.discount_percent)
        if not validated_data.get("delivery_address"):
            validated_data["delivery_address"] = client.delivery_address
        return super().create(validated_data)

    def _save_lines(self, order, lines):
        for line in lines:
            if line.get("price") is None:
                line["price"] = list_price(line["item"], order.discount_percent)
        super()._save_lines(order, lines)
