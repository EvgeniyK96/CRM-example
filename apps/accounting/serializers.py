from django.utils import timezone
from rest_framework import serializers

from core.serializers import positive

from . import services
from .models import Account, Invoice, JournalEntry, Payment, Posting


class AccountSerializer(serializers.ModelSerializer):
    type_display = serializers.CharField(source="get_type_display", read_only=True)

    class Meta:
        model = Account
        fields = "__all__"


class PostingSerializer(serializers.ModelSerializer):
    debit_code = serializers.CharField(source="debit.code", read_only=True)
    credit_code = serializers.CharField(source="credit.code", read_only=True)
    client_name = serializers.CharField(source="client.name", read_only=True, default=None)
    supplier_name = serializers.CharField(source="supplier.name", read_only=True, default=None)

    class Meta:
        model = Posting
        fields = ("id", "debit", "debit_code", "credit", "credit_code", "amount", "client", "client_name",
                  "supplier", "supplier_name", "comment")

    def validate_amount(self, value):
        return positive(value, "Сумма проводки должна быть больше нуля.")


class JournalEntrySerializer(serializers.ModelSerializer):
    postings = PostingSerializer(many=True)
    source_display = serializers.CharField(source="get_source_type_display", read_only=True)
    created_by_name = serializers.CharField(source="created_by.username", read_only=True, default=None)
    total = serializers.SerializerMethodField()

    class Meta:
        model = JournalEntry
        fields = ("id", "date", "description", "source_type", "source_display", "source_id", "postings", "total",
                  "created_by_name", "created_at")
        read_only_fields = ("source_type", "source_id")

    def get_total(self, entry):
        return f"{sum((p.amount for p in entry.postings.all()), 0):.2f}"

    def create(self, validated_data):
        """Только ручные операции — автопроводки создаёт система."""
        lines = [
            services.Line(p["debit"].code, p["credit"].code, p["amount"], client=p.get("client"),
                          supplier=p.get("supplier"), comment=p.get("comment", ""))
            for p in validated_data["postings"]
        ]
        return services.create_manual_entry(
            validated_data["date"], validated_data["description"], lines, validated_data.get("created_by"),
        )


class InvoiceSerializer(serializers.ModelSerializer):
    client_name = serializers.CharField(source="client.name", read_only=True)
    shipment_number = serializers.CharField(source="shipment.number", read_only=True, default=None)
    order = serializers.IntegerField(source="shipment.order_id", read_only=True, default=None)
    order_number = serializers.CharField(source="shipment.order.number", read_only=True, default=None)
    paid = serializers.DecimalField(max_digits=14, decimal_places=2, read_only=True)
    remaining = serializers.SerializerMethodField()
    status = serializers.SerializerMethodField()
    days_overdue = serializers.SerializerMethodField()

    class Meta:
        model = Invoice
        fields = ("id", "number", "client", "client_name", "shipment", "shipment_number", "order", "order_number",
                  "date", "due_date", "amount", "paid", "remaining", "status", "days_overdue")

    def get_remaining(self, inv):
        return f"{inv.amount - inv.paid:.2f}"

    def get_status(self, inv):
        if inv.paid >= inv.amount:
            return "paid"
        return "partial" if inv.paid > 0 else "unpaid"

    def get_days_overdue(self, inv):
        if inv.paid >= inv.amount:
            return 0
        return max((timezone.localdate() - inv.due_date).days, 0)


class PaymentSerializer(serializers.ModelSerializer):
    direction_display = serializers.CharField(source="get_direction_display", read_only=True)
    method_display = serializers.CharField(source="get_method_display", read_only=True)
    client_name = serializers.CharField(source="client.name", read_only=True, default=None)
    supplier_name = serializers.CharField(source="supplier.name", read_only=True, default=None)
    invoice_number = serializers.CharField(source="invoice.number", read_only=True, default=None)
    created_by_name = serializers.CharField(source="created_by.username", read_only=True, default=None)
    allocations = serializers.SerializerMethodField()

    class Meta:
        model = Payment
        fields = ("id", "number", "direction", "direction_display", "method", "method_display", "date", "amount",
                  "client", "client_name", "supplier", "supplier_name", "invoice", "invoice_number", "comment",
                  "allocations", "created_by_name", "created_at")

    def get_allocations(self, payment):
        return [{"invoice": a.invoice_id, "invoice_number": a.invoice.number, "amount": f"{a.amount:.2f}"}
                for a in payment.allocations.all()]

    def validate_amount(self, value):
        return positive(value, "Сумма платежа должна быть больше нуля.")

    def validate_date(self, value):
        if value > timezone.localdate():
            raise serializers.ValidationError("Платёж не может быть будущей датой.")
        return value

    def validate(self, attrs):
        direction = attrs["direction"]
        if direction == Payment.Direction.INCOMING:
            if not attrs.get("client"):
                raise serializers.ValidationError({"client": "Укажите клиента."})
            attrs["supplier"] = None
            invoice = attrs.get("invoice")
            if invoice and invoice.client_id != attrs["client"].pk:
                raise serializers.ValidationError({"invoice": "Счёт выставлен другому клиенту."})
        else:
            if not attrs.get("supplier"):
                raise serializers.ValidationError({"supplier": "Укажите поставщика."})
            attrs["client"] = None
            attrs["invoice"] = None
        return attrs

    def create(self, validated_data):
        return services.register_payment(super().create(validated_data))


class PeriodSerializer(serializers.Serializer):
    """Период отчёта; по умолчанию — с начала текущего месяца по сегодня."""

    date_from = serializers.DateField(required=False)
    date_to = serializers.DateField(required=False)

    def validate(self, attrs):
        today = timezone.localdate()
        attrs.setdefault("date_from", today.replace(day=1))
        attrs.setdefault("date_to", today)
        if attrs["date_from"] > attrs["date_to"]:
            raise serializers.ValidationError("Начало периода позже конца.")
        return attrs
