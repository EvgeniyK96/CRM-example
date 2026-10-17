from django.core.management import call_command
from django.core.management.base import BaseCommand
from django.db import transaction

from apps.accounts.models import User
from apps.sales import services
from apps.sales.models import SalesOrder, Shipment


class Command(BaseCommand):
    help = "Отгрузка готовых к отгрузке заказов (после производства)"

    @transaction.atomic
    def handle(self, *args, **options):
        call_command("seed_production", stdout=self.stdout)
        if Shipment.objects.exists():
            self.stdout.write("Отгрузки уже есть — пропускаю")
            return
        storekeeper = User.objects.filter(role="storekeeper").first()
        shipped = 0
        for order in SalesOrder.objects.filter(status=SalesOrder.Status.READY):
            services.ship(order, storekeeper, vehicle="ГАЗель 123 ABC 02", driver="Сидоров А. В.")
            shipped += 1
        self.stdout.write(self.style.SUCCESS(f"Отгружено заказов: {shipped}"))
