from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from apps.accounts.permissions import HasRole, ReadAnyWriteRoles
from core.views import CreatedByMixin, DraftOnlyDestroyMixin

from . import services
from .filters import SalesOrderFilter, ShipmentFilter
from .models import Client, SalesOrder, Shipment
from .serializers import ClientSerializer, SalesOrderSerializer, ShipmentSerializer, ShipSerializer

SalesWrite = ReadAnyWriteRoles("sales")


class ClientViewSet(viewsets.ModelViewSet):
    queryset = Client.objects.all()
    serializer_class = ClientSerializer
    permission_classes = [SalesWrite]
    filterset_fields = ["kind", "is_active"]
    search_fields = ["name", "tax_id", "contact_person", "phone"]


class SalesOrderViewSet(CreatedByMixin, DraftOnlyDestroyMixin, viewsets.ModelViewSet):
    """Заказы клиентов: новый → подтверждён / готов к отгрузке → … → отгружен (или отменён)."""

    queryset = SalesOrder.objects.select_related("client", "created_by", "confirmed_by", "shipment").prefetch_related(
        "lines__item__unit"
    )
    serializer_class = SalesOrderSerializer
    permission_classes = [SalesWrite]
    filterset_class = SalesOrderFilter
    search_fields = ["number", "client__name", "comment"]
    ordering_fields = ["created_at", "delivery_date"]

    def get_permissions(self):
        # Отгружает склад, а не менеджер
        if self.action == "ship":
            return [HasRole("storekeeper")()]
        return super().get_permissions()

    def _respond(self, order):
        return Response(self.get_serializer(self.get_queryset().get(pk=order.pk)).data)

    @action(detail=True, methods=["get"])
    def availability(self, request, pk=None):
        """Наличие готовой продукции на дату отгрузки с учётом резервов других заказов."""
        return Response(services.availability(self.get_object()))

    @action(detail=True, methods=["post"])
    def confirm(self, request, pk=None):
        return self._respond(services.confirm(self.get_object(), request.user))

    @action(detail=True, methods=["post"])
    def reopen(self, request, pk=None):
        return self._respond(services.reopen(self.get_object()))

    @action(detail=True, methods=["post"])
    def cancel(self, request, pk=None):
        return self._respond(services.cancel(self.get_object()))

    @action(detail=True, methods=["post"], serializer_class=ShipSerializer)
    def ship(self, request, pk=None):
        params = ShipSerializer(data=request.data)
        params.is_valid(raise_exception=True)
        shipment = services.ship(self.get_object(), request.user, **params.validated_data)
        return Response(ShipmentSerializer(shipment).data, status=201)


class ShipmentViewSet(viewsets.ReadOnlyModelViewSet):
    """Журнал отгрузок (расходные накладные). Создаются только действием «отгрузить» на заказе."""

    queryset = Shipment.objects.select_related("order__client", "created_by").prefetch_related(
        "items__order_line__item__unit", "items__move__lot"
    )
    serializer_class = ShipmentSerializer
    filterset_class = ShipmentFilter
    search_fields = ["number", "order__number", "order__client__name", "driver", "vehicle"]
    ordering_fields = ["date", "number"]
