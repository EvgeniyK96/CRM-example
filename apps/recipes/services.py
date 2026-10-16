"""Бизнес-логика рецептур: версии, активация, расчёт потребности в сырье."""

from decimal import ROUND_HALF_UP, Decimal

from django.db import transaction
from django.db.models import Max
from django.utils import timezone

from .models import Recipe, RecipeLine

QTY = Decimal("0.001")


class RecipeError(Exception):
    pass


def next_version(product) -> int:
    current = Recipe.objects.filter(product=product).aggregate(v=Max("version"))["v"]
    return (current or 0) + 1


@transaction.atomic
def activate(recipe: Recipe) -> Recipe:
    """Вводит черновик в действие; прежняя активная версия уходит в архив."""
    # Блокируем все версии продукта, чтобы две параллельные активации не столкнулись
    versions = list(Recipe.objects.select_for_update().filter(product_id=recipe.product_id))
    recipe = next(r for r in versions if r.pk == recipe.pk)

    if recipe.status != Recipe.Status.DRAFT:
        raise RecipeError("Активировать можно только черновик.")
    if not recipe.lines.exists():
        raise RecipeError("В рецептуре нет ни одной строки сырья.")

    Recipe.objects.filter(product_id=recipe.product_id, status=Recipe.Status.ACTIVE).update(
        status=Recipe.Status.ARCHIVED
    )
    recipe.status = Recipe.Status.ACTIVE
    recipe.activated_at = timezone.now()
    recipe.save(update_fields=["status", "activated_at"])
    return recipe


@transaction.atomic
def copy_as_draft(recipe: Recipe, user=None) -> Recipe:
    """Создаёт новую версию-черновик на основе существующей рецептуры."""
    new = Recipe.objects.create(
        product=recipe.product,
        version=next_version(recipe.product),
        output_qty=recipe.output_qty,
        note=recipe.note,
        created_by=user,
    )
    RecipeLine.objects.bulk_create(
        RecipeLine(recipe=new, ingredient_id=line.ingredient_id, quantity=line.quantity, loss_percent=line.loss_percent)
        for line in recipe.lines.all()
    )
    return new


def calculate(recipe: Recipe, qty: Decimal) -> list[dict]:
    """Потребность в сырье на выпуск qty единиц продукта (брутто, с учётом потерь)."""
    if qty <= 0:
        raise RecipeError("Количество должно быть больше нуля.")
    factor = qty / recipe.output_qty
    return [
        {
            "ingredient": line.ingredient_id,
            "ingredient_name": line.ingredient.name,
            "unit_code": line.ingredient.unit.code,
            "quantity": (line.gross_quantity * factor).quantize(QTY, ROUND_HALF_UP),
        }
        for line in recipe.lines.select_related("ingredient__unit")
    ]
