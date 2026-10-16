from decimal import Decimal

from django.core.management import call_command
from django.core.management.base import BaseCommand
from django.db import transaction

from apps.catalog.models import Item
from apps.recipes import services
from apps.recipes.models import Recipe, RecipeLine

# Учебные рецептуры: продукт → (выход партии, [(сырьё, количество нетто, потери %)])
RECIPES = {
    "PRD-001": (10, [("RAW-001", 3.5, 2), ("RAW-006", 3, 1), ("RAW-013", 20, 3), ("RAW-007", 4, 1),
                     ("RAW-003", 2.5, 0), ("RAW-015", 0.02, 0)]),
    "PRD-002": (10, [("RAW-001", 3, 2), ("RAW-004", 1, 1), ("RAW-003", 2, 0), ("RAW-013", 25, 3),
                     ("RAW-006", 1.5, 1), ("RAW-009", 4, 1), ("RAW-019", 0.05, 0)]),
    "PRD-003": (100, [("RAW-001", 1.2, 2), ("RAW-006", 1, 1), ("RAW-013", 40, 3), ("RAW-007", 1, 1),
                      ("RAW-008", 2, 2), ("RAW-003", 0.8, 0)]),
    "PRD-004": (100, [("RAW-001", 7, 2), ("RAW-004", 1.5, 1), ("RAW-003", 2.5, 0), ("RAW-005", 1, 1),
                      ("RAW-013", 20, 3), ("RAW-006", 0.8, 1), ("RAW-024", 3, 2), ("RAW-018", 0.1, 0)]),
    "PRD-005": (100, [("RAW-001", 4, 2), ("RAW-004", 1, 1), ("RAW-003", 1.5, 0), ("RAW-016", 0.08, 0),
                      ("RAW-017", 0.05, 0), ("RAW-006", 0.8, 1), ("RAW-013", 15, 3), ("RAW-025", 1, 2)]),
    "PRD-006": (100, [("RAW-001", 6, 2), ("RAW-002", 1, 1), ("RAW-013", 10, 3), ("RAW-012", 0.3, 0),
                      ("RAW-003", 4, 0), ("RAW-011", 3, 1), ("RAW-014", 0.5, 1)]),
    "PRD-007": (50, [("RAW-001", 3, 2), ("RAW-013", 10, 3), ("RAW-010", 4, 1), ("RAW-006", 2, 1),
                     ("RAW-014", 0.4, 1), ("RAW-023", 1, 2)]),
    "PRD-008": (100, [("RAW-001", 6, 2), ("RAW-007", 3, 1), ("RAW-021", 0.2, 0), ("RAW-003", 1, 0),
                      ("RAW-006", 0.6, 1), ("RAW-013", 15, 3), ("RAW-022", 0.8, 2), ("RAW-020", 0.06, 0)]),
    "PRD-009": (100, [("RAW-001", 5, 2), ("RAW-006", 3, 1), ("RAW-007", 2, 1), ("RAW-021", 0.15, 0),
                      ("RAW-003", 0.5, 0), ("RAW-020", 0.05, 0), ("RAW-013", 10, 3)]),
}


class Command(BaseCommand):
    help = "Создаёт и активирует учебные рецептуры для всей готовой продукции"

    @transaction.atomic
    def handle(self, *args, **options):
        call_command("seed_catalog", stdout=self.stdout)
        items = {i.code: i for i in Item.objects.all()}
        created = 0
        for code, (output, lines) in RECIPES.items():
            product = items[code]
            if Recipe.objects.filter(product=product).exists():
                continue
            recipe = Recipe.objects.create(product=product, version=1, output_qty=output)
            RecipeLine.objects.bulk_create(
                RecipeLine(recipe=recipe, ingredient=items[raw], quantity=Decimal(str(qty)), loss_percent=loss)
                for raw, qty, loss in lines
            )
            services.activate(recipe)
            created += 1
        self.stdout.write(self.style.SUCCESS(f"Рецептур создано: {created}"))
