import django_filters as filters

from .models import PurchaseOrder, Receipt


class PurchaseOrderFilter(filters.FilterSet):
    status = filters.MultipleChoiceFilter(choices=PurchaseOrder.Status.choices)
    expected_from = filters.DateFilter(field_name="expected_date", lookup_expr="gte")
    expected_to = filters.DateFilter(field_name="expected_date", lookup_expr="lte")

    class Meta:
        model = PurchaseOrder
        fields = ["supplier"]


class ReceiptFilter(filters.FilterSet):
    status = filters.MultipleChoiceFilter(choices=Receipt.Status.choices)
    date_from = filters.DateFilter(field_name="date", lookup_expr="gte")
    date_to = filters.DateFilter(field_name="date", lookup_expr="lte")

    class Meta:
        model = Receipt
        fields = ["supplier", "order"]
