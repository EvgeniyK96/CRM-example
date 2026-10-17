import django_filters as filters

from .models import ProductionTask


class ProductionTaskFilter(filters.FilterSet):
    status = filters.MultipleChoiceFilter(choices=ProductionTask.Status.choices)
    date_from = filters.DateFilter(field_name="planned_date", lookup_expr="gte")
    date_to = filters.DateFilter(field_name="planned_date", lookup_expr="lte")
    order = filters.NumberFilter(field_name="allocations__order_line__order", distinct=True, label="Заказ клиента")

    class Meta:
        model = ProductionTask
        fields = ["department", "product"]
