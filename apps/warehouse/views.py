from decimal import Decimal

from django.db.models import BooleanField, Case, F, OuterRef, Q, Subquery, Sum, Value, When
from django.db.models.functions import Coalesce
from django.utils import timezone
from rest_framework import mixins, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from apps.accounts.permissions import ReadAnyWriteRoles
from apps.catalog.models import Item

from . import services
from .filters import LotFilter, StockFilter, StockMoveFilter
from .models import QTY_FIELD, Lot, StockMove, balance_expr
from .serializers import LotSerializer, StockMoveSerializer, StockSerializer, WriteOffSerializer


class LotViewSet(viewsets.ReadOnlyModelViewSet):
    """Партии с остатками. Создаются только документами (приёмка, выпуск), вручную — нет."""

    queryset = Lot.objects.select_related("item__unit", "supplier").with_balance()
    serializer_class = LotSerializer
    permission_classes = [ReadAnyWriteRoles("storekeeper")]
    filterset_class = LotFilter
    search_fields = ["number", "item__name", "item__code"]
    ordering_fields = ["expiry_date", "date", "balance"]

    @action(detail=True, methods=["post"], serializer_class=WriteOffSerializer)
    def write_off(self, request, pk=None):
        params = WriteOffSerializer(data=request.data)
        params.is_valid(raise_exception=True)
        services.write_off(self.get_object(), user=request.user, **params.validated_data)
        return Response(LotSerializer(self.get_queryset().get(pk=pk)).data)


class StockViewSet(mixins.ListModelMixin, viewsets.GenericViewSet):
    """Сводные остатки по номенклатуре: всего, доступно (непросроченное), просрочено, ниже минимума."""

    serializer_class = StockSerializer
    filterset_class = StockFilter
    search_fields = ["code", "name"]
    ordering_fields = ["name", "code", "balance", "nearest_expiry"]

    def get_queryset(self):
        today = timezone.localdate()
        nearest = Lot.objects.filter(item=OuterRef("pk")).usable(today).values("expiry_date")[:1]
        return (
            Item.objects.filter(is_active=True)
            .select_related("unit")
            .annotate(
                balance=balance_expr("lots__moves__quantity"),
                available=Coalesce(
                    Sum("lots__moves__quantity", filter=Q(lots__expiry_date__gte=today)),
                    Value(Decimal(0)),
                    output_field=QTY_FIELD,
                ),
                nearest_expiry=Subquery(nearest),
            )
            .annotate(
                expired=F("balance") - F("available"),
                below_min=Case(When(available__lt=F("min_stock"), then=True), default=False, output_field=BooleanField()),
            )
            .order_by("name")
        )


class StockMoveViewSet(viewsets.ReadOnlyModelViewSet):
    """Журнал движений. Записи неизменяемы: ошибку исправляют встречным движением."""

    queryset = StockMove.objects.select_related("lot__item__unit", "created_by")
    serializer_class = StockMoveSerializer
    filterset_class = StockMoveFilter
    search_fields = ["lot__number", "lot__item__name", "reference"]
