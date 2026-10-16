from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from apps.accounts.permissions import ReadAnyWriteRoles
from core.views import CreatedByMixin, DraftOnlyDestroyMixin

from . import services
from .filters import SalesOrderFilter
from .models import Client, SalesOrder
from .serializers import ClientSerializer, SalesOrderSerializer

SalesWrite = ReadAnyWriteRoles("sales")


class ClientViewSet(viewsets.ModelViewSet):
    queryset = Client.objects.all()
    serializer_class = ClientSerializer
    permission_classes = [SalesWrite]
    filterset_fields = ["kind", "is_active"]
    search_fields = ["name", "tax_id", "contact_person", "phone"]


class SalesOrderViewSet(CreatedByMixin, DraftOnlyDestroyMixin, viewsets.ModelViewSet):
    """Заказы клиентов: новый → подтверждён / готов к отгрузке → … → отгружен (или отменён)."""

    queryset = SalesOrder.objects.select_related("client", "created_by", "confirmed_by").prefetch_related(
        "lines__item__unit"
    )
    serializer_class = SalesOrderSerializer
    permission_classes = [SalesWrite]
    filterset_class = SalesOrderFilter
    search_fields = ["number", "client__name", "comment"]
    ordering_fields = ["created_at", "delivery_date"]

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
