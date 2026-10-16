from django.db import models


class Unit(models.Model):
    code = models.CharField("Обозначение", max_length=10, unique=True)
    name = models.CharField("Название", max_length=50)

    class Meta:
        verbose_name = "Единица измерения"
        verbose_name_plural = "Единицы измерения"
        ordering = ["code"]

    def __str__(self):
        return self.code


class ItemKind(models.TextChoices):
    RAW = "raw", "Сырьё"
    PRODUCT = "product", "Готовая продукция"


class Category(models.Model):
    name = models.CharField("Название", max_length=120)
    kind = models.CharField("Тип номенклатуры", max_length=10, choices=ItemKind.choices)

    class Meta:
        verbose_name = "Категория"
        verbose_name_plural = "Категории"
        ordering = ["kind", "name"]
        constraints = [models.UniqueConstraint(fields=["name", "kind"], name="unique_category_per_kind")]

    def __str__(self):
        return self.name


class Item(models.Model):
    """Номенклатура: сырьё или готовая продукция."""

    kind = models.CharField("Тип", max_length=10, choices=ItemKind.choices)
    code = models.CharField("Артикул", max_length=30, unique=True)
    name = models.CharField("Название", max_length=200)
    category = models.ForeignKey(
        Category, verbose_name="Категория", null=True, blank=True, on_delete=models.PROTECT, related_name="items"
    )
    unit = models.ForeignKey(Unit, verbose_name="Единица измерения", on_delete=models.PROTECT, related_name="items")
    department = models.ForeignKey(
        "hr.Department", verbose_name="Цех-изготовитель", null=True, blank=True,
        on_delete=models.PROTECT, related_name="products", limit_choices_to={"is_production": True},
    )
    shelf_life_days = models.PositiveIntegerField("Срок годности, дней")
    min_stock = models.DecimalField("Минимальный остаток", max_digits=12, decimal_places=3, default=0)
    sale_price = models.DecimalField("Отпускная цена", max_digits=12, decimal_places=2, default=0)
    is_active = models.BooleanField("Используется", default=True)

    class Meta:
        verbose_name = "Номенклатура"
        verbose_name_plural = "Номенклатура"
        ordering = ["kind", "name"]

    def __str__(self):
        return f"{self.name} ({self.unit.code})"


class Supplier(models.Model):
    name = models.CharField("Название", max_length=200, unique=True)
    tax_id = models.CharField("БИН/ИНН", max_length=20, blank=True)
    contact_person = models.CharField("Контактное лицо", max_length=120, blank=True)
    phone = models.CharField("Телефон", max_length=30, blank=True)
    email = models.EmailField("Email", blank=True)
    address = models.CharField("Адрес", max_length=255, blank=True)
    note = models.TextField("Примечание", blank=True)
    is_active = models.BooleanField("Активен", default=True)

    class Meta:
        verbose_name = "Поставщик"
        verbose_name_plural = "Поставщики"
        ordering = ["name"]

    def __str__(self):
        return self.name
