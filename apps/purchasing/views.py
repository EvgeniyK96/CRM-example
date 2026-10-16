from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from apps.accounts.permissions import ReadAnyWriteRoles
from core.views import CreatedByMixin, DraftOnlyDestroyMixin

from . import services
from .models import PurchaseOrder, Receipt
from .serializers import PurchaseOrderSerializer, ReceiptSerializer

StorekeeperWrite = ReadAnyWriteRoles("storekeeper")


class PurchaseOrderViewSet(CreatedByMixin, DraftOnlyDestroyMixin, viewsets.ModelViewSet):
    """Заявки поставщикам: черновик → отправлена → получена частично / получена (или отменена)."""

    queryset = PurchaseOrder.objects.select_related("supplier", "created_by").prefetch_related("lines__item__unit")
    serializer_class = PurchaseOrderSerializer
    permission_classes = [StorekeeperWrite]
    filterset_fields = ["status", "supplier"]
    search_fields = ["number", "supplier__name", "comment"]
    ordering_fields = ["created_at", "expected_date"]

    @action(detail=True, methods=["post"])
    def send(self, request, pk=None):
        return Response(self.get_serializer(services.send(self.get_object())).data)

    @action(detail=True, methods=["post"])
    def cancel(self, request, pk=None):
        return Response(self.get_serializer(services.cancel(self.get_object())).data)

    @action(detail=True, methods=["post"])
    def receive(self, request, pk=None):
        """Создаёт черновик приёмки на неполученный остаток заявки."""
        receipt = services.create_receipt(self.get_object(), request.user)
        return Response(ReceiptSerializer(receipt).data, status=status.HTTP_201_CREATED)


class ReceiptViewSet(CreatedByMixin, DraftOnlyDestroyMixin, viewsets.ModelViewSet):
    """Приёмки сырья. Проведение создаёт партии на складе; проведённая приёмка неизменяема."""

    queryset = Receipt.objects.select_related("supplier", "order", "created_by", "posted_by").prefetch_related(
        "lines__item__unit", "lines__lot"
    )
    serializer_class = ReceiptSerializer
    permission_classes = [StorekeeperWrite]
    filterset_fields = ["status", "supplier", "order"]
    search_fields = ["number", "invoice_number", "supplier__name"]
    ordering_fields = ["date", "posted_at"]

    @action(detail=True, methods=["post"])
    def post(self, request, pk=None):
        receipt = services.post_receipt(self.get_object(), request.user)
        return Response(self.get_serializer(self.get_queryset().get(pk=receipt.pk)).data)
