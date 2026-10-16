import django_filters as filters
from django.utils import timezone

from apps.catalog.models import Item, ItemKind

from .models import Lot, MoveKind, StockMove


class LotFilter(filters.FilterSet):
    in_stock = filters.BooleanFilter(method="filter_in_stock", label="Есть остаток")
    expired = filters.BooleanFilter(method="filter_expired", label="Просрочена")
    kind = filters.ChoiceFilter(field_name="item__kind", choices=ItemKind.choices)

    class Meta:
        model = Lot
        fields = ["item", "supplier"]

    def filter_in_stock(self, qs, name, value):
        return qs.filter(balance__gt=0) if value else qs.filter(balance__lte=0)

    def filter_expired(self, qs, name, value):
        today = timezone.localdate()
        return qs.filter(expiry_date__lt=today) if value else qs.filter(expiry_date__gte=today)


class StockFilter(filters.FilterSet):
    below_min = filters.BooleanFilter(field_name="below_min")
    in_stock = filters.BooleanFilter(method="filter_in_stock")

    class Meta:
        model = Item
        fields = ["kind", "category"]

    def filter_in_stock(self, qs, name, value):
        return qs.filter(balance__gt=0) if value else qs.filter(balance__lte=0)


class StockMoveFilter(filters.FilterSet):
    item = filters.NumberFilter(field_name="lot__item")
    item_kind = filters.ChoiceFilter(field_name="lot__item__kind", choices=ItemKind.choices)
    kind = filters.MultipleChoiceFilter(choices=MoveKind.choices)
    date_from = filters.DateFilter(field_name="created_at__date", lookup_expr="gte")
    date_to = filters.DateFilter(field_name="created_at__date", lookup_expr="lte")

    class Meta:
        model = StockMove
        fields = ["lot"]
