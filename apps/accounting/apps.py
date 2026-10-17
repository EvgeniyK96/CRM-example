from django.apps import AppConfig


class AccountingConfig(AppConfig):
    name = "apps.accounting"
    verbose_name = "Бухгалтерия"

    def ready(self):
        from . import receivers  # noqa: F401 — подписка на сигналы склада, закупок, производства, продаж
