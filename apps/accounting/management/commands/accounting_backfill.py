from django.core.management.base import BaseCommand
from django.db import transaction

from apps.accounting import services
from apps.accounting.models import Invoice, JournalEntry
from apps.production.models import ProductionTask
from apps.purchasing.models import Receipt
from apps.sales.models import Shipment
from apps.warehouse.models import Lot, MoveKind, StockMove


class Command(BaseCommand):
    help = "Создаёт проводки и счета для операций, проведённых до появления бухгалтерии. Повторный запуск безопасен."

    @transaction.atomic
    def handle(self, *args, **options):
        entries, invoices = JournalEntry.objects.count(), Invoice.objects.count()

        for lot in Lot.objects.filter(moves__kind=MoveKind.ADJUSTMENT).distinct().select_related("item"):
            services.on_opening_balance(lot)
        for receipt in Receipt.objects.filter(status=Receipt.Status.POSTED).order_by("date", "pk"):
            services.on_receipt_posted(receipt)
        tasks = ProductionTask.objects.select_related("product__unit").order_by("started_at")
        for task in tasks.filter(started_at__isnull=False):
            services.on_task_started(task)
        for task in tasks.filter(status=ProductionTask.Status.DONE):
            services.on_task_finished(task)
        for shipment in Shipment.objects.select_related("order__client").order_by("date", "pk"):
            services.on_shipment_created(shipment)
        for move in StockMove.objects.filter(kind=MoveKind.WRITE_OFF).select_related("lot__item"):
            services.on_stock_written_off(move)

        self.stdout.write(self.style.SUCCESS(
            f"Операций создано: {JournalEntry.objects.count() - entries}, счетов: {Invoice.objects.count() - invoices}"
        ))
