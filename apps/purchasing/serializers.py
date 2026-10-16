from rest_framework import serializers

from apps.catalog.models import ItemKind
from core.serializers import LinesWriteMixin, positive

from .models import PurchaseOrder, PurchaseOrderLine, Receipt, ReceiptLine
from .services import received_qty


class RawLineMixin(serializers.Serializer):
    item_name = serializers.CharField(source="item.name", read_only=True)
    unit_code = serializers.CharField(source="item.unit.code", read_only=True)
    amount = serializers.SerializerMethodField()

    def get_amount(self, line):
        return f"{line.quantity * line.price:.2f}"

    def validate_item(self, value):
        if value.kind != ItemKind.RAW:
            raise serializers.ValidationError("Закупать можно только сырьё.")
        return value

    def validate_quantity(self, value):
        return positive(value)

    def validate_price(self, value):
        if value < 0:
            raise serializers.ValidationError("Цена не может быть отрицательной.")
        return value


def document_total(doc):
    return f"{sum((line.quantity * line.price for line in doc.lines.all()), 0):.2f}"


class PurchaseOrderLineSerializer(RawLineMixin, serializers.ModelSerializer):
    received = serializers.SerializerMethodField()

    class Meta:
        model = PurchaseOrderLine
        fields = ("id", "item", "item_name", "unit_code", "quantity", "price", "amount", "received")

    def get_received(self, line):
        return received_qty(line)


class PurchaseOrderSerializer(LinesWriteMixin, serializers.ModelSerializer):
    lines_parent_field = "order"
    lines_unique_field = "item"
    not_editable_message = "Изменять можно только черновик заявки."

    lines = PurchaseOrderLineSerializer(many=True, required=False)
    supplier_name = serializers.CharField(source="supplier.name", read_only=True)
    status_display = serializers.CharField(source="get_status_display", read_only=True)
    created_by_name = serializers.CharField(source="created_by.username", read_only=True, default=None)
    total = serializers.SerializerMethodField()

    class Meta:
        model = PurchaseOrder
        fields = (
            "id", "number", "supplier", "supplier_name", "status", "status_display", "expected_date", "comment",
            "lines", "total", "created_by_name", "created_at",
        )
        read_only_fields = ("status",)

    def get_total(self, order):
        return document_total(order)


class ReceiptLineSerializer(RawLineMixin, serializers.ModelSerializer):
    lot_number = serializers.CharField(source="lot.number", read_only=True, default=None)

    class Meta:
        model = ReceiptLine
        fields = (
            "id", "item", "item_name", "unit_code", "quantity", "price", "amount", "expiry_date", "order_line",
            "lot", "lot_number",
        )
        read_only_fields = ("lot",)


class ReceiptSerializer(LinesWriteMixin, serializers.ModelSerializer):
    lines_parent_field = "receipt"
    not_editable_message = "Проведённую приёмку изменить нельзя."

    lines = ReceiptLineSerializer(many=True, required=False)
    supplier_name = serializers.CharField(source="supplier.name", read_only=True)
    order_number = serializers.CharField(source="order.number", read_only=True, default=None)
    status_display = serializers.CharField(source="get_status_display", read_only=True)
    created_by_name = serializers.CharField(source="created_by.username", read_only=True, default=None)
    posted_by_name = serializers.CharField(source="posted_by.username", read_only=True, default=None)
    total = serializers.SerializerMethodField()

    class Meta:
        model = Receipt
        fields = (
            "id", "number", "supplier", "supplier_name", "order", "order_number", "date", "invoice_number", "status",
            "status_display", "comment", "lines", "total", "created_by_name", "posted_by_name", "posted_at",
        )
        read_only_fields = ("order", "status", "posted_at")

    def get_total(self, receipt):
        return document_total(receipt)

    def validate(self, attrs):
        attrs = super().validate(attrs)
        order = self.instance.order if self.instance else None
        if order and attrs.get("supplier", order.supplier) != order.supplier:
            raise serializers.ValidationError({"supplier": "Поставщик должен совпадать с поставщиком заявки."})
        order_lines = {ol.item_id: ol for ol in order.lines.all()} if order else {}
        for line in attrs.get("lines", []):
            order_line = line.get("order_line")
            if order_line and (order_line.order_id != getattr(order, "pk", None) or order_line.item_id != line["item"].pk):
                raise serializers.ValidationError({"lines": "Строка не соответствует заявке, по которой создана приёмка."})
            # Клиент не прислал связь со строкой заявки — восстанавливаем по сырью,
            # иначе после проведения заявка не узнает, что поставка пришла
            if not order_line and line["item"].pk in order_lines:
                line["order_line"] = order_lines[line["item"].pk]
        return attrs
