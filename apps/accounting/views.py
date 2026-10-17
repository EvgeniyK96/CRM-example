from django.shortcuts import get_object_or_404
from rest_framework import mixins, viewsets
from rest_framework.exceptions import ValidationError
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.accounts.permissions import HasRole, RoleAccess
from core.views import CreatedByMixin

from . import reports, services
from .filters import InvoiceFilter, JournalEntryFilter, PaymentFilter
from .models import Account, JournalEntry, Payment
from .serializers import (
    AccountSerializer,
    InvoiceSerializer,
    JournalEntrySerializer,
    PaymentSerializer,
    PeriodSerializer,
)

AccountantOnly = HasRole("accountant")
# Счета и платежи видит и отдел продаж (долги клиентов), вносит — бухгалтерия
SalesCanRead = RoleAccess(read=("sales",), write=("accountant",))


class AccountViewSet(viewsets.ModelViewSet):
    queryset = Account.objects.all()
    serializer_class = AccountSerializer
    permission_classes = [AccountantOnly]
    filterset_fields = ["type", "is_active"]
    search_fields = ["code", "name"]


class JournalEntryViewSet(CreatedByMixin, mixins.CreateModelMixin, mixins.DestroyModelMixin,
                          viewsets.ReadOnlyModelViewSet):
    """Журнал операций. Автопроводки создаёт система; вручную — только операции без документа-основания."""

    queryset = JournalEntry.objects.select_related("created_by").prefetch_related(
        "postings__debit", "postings__credit", "postings__client", "postings__supplier"
    )
    serializer_class = JournalEntrySerializer
    permission_classes = [AccountantOnly]
    filterset_class = JournalEntryFilter
    search_fields = ["description", "postings__comment"]

    def perform_destroy(self, entry):
        if entry.source_type != JournalEntry.Source.MANUAL:
            raise ValidationError("Автоматическую операцию нельзя удалить — она связана с документом.")
        entry.delete()


class InvoiceViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = services.invoices_with_paid().select_related("client", "shipment__order")
    serializer_class = InvoiceSerializer
    permission_classes = [SalesCanRead]
    filterset_class = InvoiceFilter
    search_fields = ["number", "client__name", "shipment__number", "shipment__order__number"]
    ordering_fields = ["date", "due_date", "amount"]


class PaymentViewSet(CreatedByMixin, mixins.CreateModelMixin, viewsets.ReadOnlyModelViewSet):
    """Платежи неизменяемы: ошибку исправляют встречным платежом/ручной операцией."""

    queryset = Payment.objects.select_related("client", "supplier", "invoice", "created_by").prefetch_related(
        "allocations__invoice"
    )
    serializer_class = PaymentSerializer
    permission_classes = [SalesCanRead]
    filterset_class = PaymentFilter
    search_fields = ["number", "comment", "client__name", "supplier__name"]


def _period(request):
    params = PeriodSerializer(data=request.query_params)
    params.is_valid(raise_exception=True)
    return params.validated_data["date_from"], params.validated_data["date_to"]


class TrialBalanceView(APIView):
    permission_classes = [AccountantOnly]

    def get(self, request):
        return Response(reports.trial_balance(*_period(request)))


class AccountCardView(APIView):
    permission_classes = [AccountantOnly]

    def get(self, request):
        account = get_object_or_404(Account, pk=request.query_params.get("account"))
        return Response(reports.account_card(
            account, *_period(request), client_id=request.query_params.get("client"),
            supplier_id=request.query_params.get("supplier"),
        ))


class ReceivablesView(APIView):
    permission_classes = [SalesCanRead]

    def get(self, request):
        return Response(reports.receivables())


class PayablesView(APIView):
    permission_classes = [AccountantOnly]

    def get(self, request):
        return Response(reports.payables())


class ProfitLossView(APIView):
    permission_classes = [AccountantOnly]

    def get(self, request):
        return Response(reports.profit_and_loss(*_period(request)))
