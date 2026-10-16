from django.conf import settings
from django.db import models
from django.db.models import Q


class Recipe(models.Model):
    """Рецептура (технологическая карта) продукта. Версионируется: менять можно только черновик."""

    class Status(models.TextChoices):
        DRAFT = "draft", "Черновик"
        ACTIVE = "active", "Активна"
        ARCHIVED = "archived", "В архиве"

    product = models.ForeignKey(
        "catalog.Item", verbose_name="Продукт", on_delete=models.PROTECT, related_name="recipes",
        limit_choices_to={"kind": "product"},
    )
    version = models.PositiveIntegerField("Версия")
    status = models.CharField("Статус", max_length=10, choices=Status.choices, default=Status.DRAFT)
    output_qty = models.DecimalField("Выход партии", max_digits=12, decimal_places=3, help_text="В единицах продукта")
    note = models.TextField("Технологические указания", blank=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, verbose_name="Автор", null=True, blank=True, on_delete=models.SET_NULL,
        related_name="+",
    )
    created_at = models.DateTimeField("Создана", auto_now_add=True)
    activated_at = models.DateTimeField("Введена в действие", null=True, blank=True)

    class Meta:
        verbose_name = "Рецептура"
        verbose_name_plural = "Рецептуры"
        ordering = ["product__name", "-version"]
        constraints = [
            models.UniqueConstraint(fields=["product", "version"], name="unique_recipe_version"),
            models.UniqueConstraint(
                fields=["product"], condition=Q(status="active"), name="one_active_recipe_per_product"
            ),
            models.CheckConstraint(condition=Q(output_qty__gt=0), name="recipe_output_positive"),
        ]

    def __str__(self):
        return f"{self.product.name} v{self.version}"

    @property
    def is_editable(self):
        return self.status == self.Status.DRAFT


class RecipeLine(models.Model):
    recipe = models.ForeignKey(Recipe, verbose_name="Рецептура", on_delete=models.CASCADE, related_name="lines")
    ingredient = models.ForeignKey(
        "catalog.Item", verbose_name="Сырьё", on_delete=models.PROTECT, related_name="used_in",
        limit_choices_to={"kind": "raw"},
    )
    quantity = models.DecimalField("Количество нетто", max_digits=12, decimal_places=3)
    loss_percent = models.DecimalField("Потери, %", max_digits=5, decimal_places=2, default=0)

    class Meta:
        verbose_name = "Строка рецептуры"
        verbose_name_plural = "Строки рецептуры"
        constraints = [
            models.UniqueConstraint(fields=["recipe", "ingredient"], name="unique_ingredient_in_recipe"),
            models.CheckConstraint(condition=Q(quantity__gt=0), name="recipe_line_qty_positive"),
            models.CheckConstraint(
                condition=Q(loss_percent__gte=0, loss_percent__lt=100), name="recipe_line_loss_range"
            ),
        ]

    def __str__(self):
        return f"{self.ingredient.name}: {self.quantity}"

    @property
    def gross_quantity(self):
        """Количество брутто с учётом потерь."""
        return self.quantity * (1 + self.loss_percent / 100)
