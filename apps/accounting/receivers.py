"""Подписка бухгалтерии на события доменных модулей (подключается в AccountingConfig.ready)."""

from django.dispatch import receiver

from apps.production.signals import task_finished, task_started
from apps.purchasing.signals import receipt_posted
from apps.sales.signals import shipment_created
from apps.warehouse.signals import opening_balance_entered, stock_written_off

from . import services


@receiver(receipt_posted)
def _receipt(sender, receipt, **kwargs):
    services.on_receipt_posted(receipt)


@receiver(task_started)
def _task_started(sender, task, **kwargs):
    services.on_task_started(task)


@receiver(task_finished)
def _task_finished(sender, task, **kwargs):
    services.on_task_finished(task)


@receiver(shipment_created)
def _shipment(sender, shipment, **kwargs):
    services.on_shipment_created(shipment)


@receiver(stock_written_off)
def _write_off(sender, move, **kwargs):
    services.on_stock_written_off(move)


@receiver(opening_balance_entered)
def _opening(sender, lot, **kwargs):
    services.on_opening_balance(lot)
