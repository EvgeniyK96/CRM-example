from decimal import Decimal

from django.core.management import call_command
from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils import timezone

from apps.accounting import services
from apps.accounting.models import Invoice, Payment
from apps.accounts.models import User
from apps.catalog.models import Supplier
from apps.sales.models import Client


class Command(BaseCommand):
    help = "Платежи: частичная оплата счёта клиентом, аванс фирменного магазина, оплата поставщику"

    @transaction.atomic
    def handle(self, *args, **options):
        call_command("seed_shipping", stdout=self.stdout)
        call_command("accounting_backfill", stdout=self.stdout)
        if Payment.objects.exists():
            self.stdout.write("Платежи уже есть — пропускаю")
            return
        accountant = User.objects.filter(role="accountant").first()

        def pay(**kwargs):
            payment = Payment.objects.create(created_by=accountant, date=timezone.localdate(), **kwargs)
            services.register_payment(payment)

        if invoice := Invoice.objects.order_by("pk").first():
            pay(direction="incoming", client=invoice.client, invoice=invoice,
                amount=(invoice.amount / 2).quantize(Decimal("0.01")), comment=f"Частичная оплата по {invoice.number}")
        if brand := Client.objects.filter(kind="brand_store", invoices__isnull=True).first():
            pay(direction="incoming", client=brand, amount=Decimal(50000), method="cash", comment="Предоплата")
        if supplier := Supplier.objects.filter(name__icontains="мелькомбинат").first():
            pay(direction="outgoing", supplier=supplier, amount=Decimal(100000), comment="Оплата за муку")
        self.stdout.write(self.style.SUCCESS("Платежи созданы"))
