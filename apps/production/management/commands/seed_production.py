from decimal import Decimal

from django.core.management import call_command
from django.core.management.base import BaseCommand
from django.db import transaction

from apps.accounts.models import User
from apps.production import services
from apps.production.models import ProductionTask


class Command(BaseCommand):
    help = "Задания из потребности заказов: одно выполнено, одно в работе, остальные запланированы"

    @transaction.atomic
    def handle(self, *args, **options):
        call_command("seed_sales", stdout=self.stdout)
        if ProductionTask.objects.exists():
            self.stdout.write("Задания уже есть — пропускаю")
            return
        planner = User.objects.filter(username="shop_head").first()
        tasks = {t.product.code: t for t in services.plan_from_demand(user=planner)}

        # Вафельный торт: выполнено с небольшим браком
        if waffle := tasks.get("PRD-007"):
            services.start(waffle, planner)
            services.finish(waffle, waffle.planned_qty, Decimal(1), user=planner)
        # Тульский пряник: в работе (сырьё уже списано)
        if ginger := tasks.get("PRD-004"):
            services.start(ginger, planner)
        self.stdout.write(self.style.SUCCESS(f"Заданий создано: {len(tasks)}"))
