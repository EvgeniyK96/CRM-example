import django_filters as filters
from django.db.models import F, Q
from django.utils import timezone

from .models import Invoice, JournalEntry, Payment


class JournalEntryFilter(filters.FilterSet):
    date_from = filters.DateFilter(field_name="date", lookup_expr="gte")
    date_to = filters.DateFilter(field_name="date", lookup_expr="lte")
    source_type = filters.MultipleChoiceFilter(choices=JournalEntry.Source.choices)
    account = filters.NumberFilter(method="filter_account", label="Счёт (по дебету или кредиту)")
    client = filters.NumberFilter(field_name="postings__client", distinct=True)
    supplier = filters.NumberFilter(field_name="postings__supplier", distinct=True)

    class Meta:
        model = JournalEntry
        fields = []

    def filter_account(self, qs, name, value):
        return qs.filter(Q(postings__debit=value) | Q(postings__credit=value)).distinct()


class InvoiceFilter(filters.FilterSet):
    status = filters.ChoiceFilter(
        choices=[("unpaid", "Не оплачен"), ("partial", "Частично"), ("paid", "Оплачен"), ("open", "Не закрыт"),
                 ("overdue", "Просрочен")],
        method="filter_status",
    )
    date_from = filters.DateFilter(field_name="date", lookup_expr="gte")
    date_to = filters.DateFilter(field_name="date", lookup_expr="lte")

    class Meta:
        model = Invoice
        fields = ["client"]

    def filter_status(self, qs, name, value):
        if value == "paid":
            return qs.filter(paid__gte=F("amount"))
        if value == "partial":
            return qs.filter(paid__gt=0, paid__lt=F("amount"))
        if value == "unpaid":
            return qs.filter(paid=0)
        if value == "open":
            return qs.filter(paid__lt=F("amount"))
        return qs.filter(paid__lt=F("amount"), due_date__lt=timezone.localdate())


class PaymentFilter(filters.FilterSet):
    date_from = filters.DateFilter(field_name="date", lookup_expr="gte")
    date_to = filters.DateFilter(field_name="date", lookup_expr="lte")

    class Meta:
        model = Payment
        fields = ["direction", "method", "client", "supplier", "invoice"]
