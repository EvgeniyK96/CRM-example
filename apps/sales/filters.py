import django_filters as filters

from .models import Client, SalesOrder, Shipment


class SalesOrderFilter(filters.FilterSet):
    status = filters.MultipleChoiceFilter(choices=SalesOrder.Status.choices)
    client_kind = filters.ChoiceFilter(field_name="client__kind", choices=Client.Kind.choices)
    delivery_from = filters.DateFilter(field_name="delivery_date", lookup_expr="gte")
    delivery_to = filters.DateFilter(field_name="delivery_date", lookup_expr="lte")
    mine = filters.BooleanFilter(method="filter_mine", label="Только мои")

    class Meta:
        model = SalesOrder
        fields = ["client"]

    def filter_mine(self, qs, name, value):
        return qs.filter(created_by=self.request.user) if value else qs


class ShipmentFilter(filters.FilterSet):
    client = filters.NumberFilter(field_name="order__client")
    date_from = filters.DateFilter(field_name="date", lookup_expr="gte")
    date_to = filters.DateFilter(field_name="date", lookup_expr="lte")

    class Meta:
        model = Shipment
        fields = ["order"]
