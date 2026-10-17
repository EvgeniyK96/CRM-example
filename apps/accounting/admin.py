from django.contrib import admin

from .models import Account, Invoice, JournalEntry, Payment, PaymentAllocation, Posting


@admin.register(Account)
class AccountAdmin(admin.ModelAdmin):
    list_display = ("code", "name", "type", "is_active")
    list_filter = ("type",)


class PostingInline(admin.TabularInline):
    model = Posting
    extra = 0


@admin.register(JournalEntry)
class JournalEntryAdmin(admin.ModelAdmin):
    list_display = ("date", "description", "source_type", "source_id", "created_by")
    list_filter = ("source_type",)
    search_fields = ("description",)
    inlines = [PostingInline]


@admin.register(Invoice)
class InvoiceAdmin(admin.ModelAdmin):
    list_display = ("number", "client", "date", "due_date", "amount")
    search_fields = ("number", "client__name")


class PaymentAllocationInline(admin.TabularInline):
    model = PaymentAllocation
    extra = 0


@admin.register(Payment)
class PaymentAdmin(admin.ModelAdmin):
    list_display = ("number", "direction", "date", "amount", "client", "supplier")
    list_filter = ("direction", "method")
    inlines = [PaymentAllocationInline]
