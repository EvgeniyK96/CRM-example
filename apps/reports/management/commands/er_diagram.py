"""
Генерирует ER-диаграммы (Mermaid) из моделей Django — документация не расходится с кодом.

    python manage.py er_diagram --output docs/ER.md
"""

from pathlib import Path

from django.apps import apps
from django.core.management.base import BaseCommand
from django.db import models

# Диаграммы по доменам: одна большая схема на ~40 таблиц нечитаема
GROUPS = [
    ("Пользователи и кадры", ["accounts", "hr"]),
    ("Каталог и рецептуры", ["catalog", "recipes"]),
    ("Склад и закупки", ["warehouse", "purchasing"]),
    ("Продажи, отгрузка и производство", ["sales", "production"]),
    ("Бухгалтерия и зарплата", ["accounting", "payroll"]),
]

AUDIT_FIELDS = {"created_by", "posted_by", "started_by", "finished_by", "confirmed_by"}

# У пользователя много служебных полей AbstractUser — показываем значимые
FIELDS_ONLY = {"User": ["id", "username", "first_name", "last_name", "role", "is_active"]}

TYPES = [
    (models.AutoField, "int"), (models.BigAutoField, "int"), (models.BooleanField, "bool"),
    (models.DecimalField, "decimal"), (models.IntegerField, "int"), (models.DateTimeField, "datetime"),
    (models.DateField, "date"), (models.TextField, "text"), (models.CharField, "string"),
]


def field_type(field) -> str:
    for cls, name in TYPES:
        if isinstance(field, cls):
            return name
    return "string"


def attributes(model) -> list[str]:
    only = FIELDS_ONLY.get(model.__name__)
    rows = []
    for field in model._meta.concrete_fields:
        if only and field.name not in only:
            continue
        label = str(field.verbose_name).replace('"', "'")
        if field.primary_key:
            rows.append(f"int {field.attname} PK")
        elif field.is_relation:
            rows.append(f'int {field.attname} FK "{label}"')
        else:
            unique = " UK" if field.unique else ""
            rows.append(f'{field_type(field)} {field.name}{unique} "{label}"')
    return rows


def relations(model) -> list[tuple[str, str, str, str]]:
    """(родитель, кардинальность, потомок, подпись) для FK и OneToOne модели."""
    result = []
    for field in model._meta.concrete_fields:
        if not field.is_relation or field.related_model is None:
            continue
        if field.name in AUDIT_FIELDS:  # «кто провёл» — есть почти у каждого документа, линии только мешают
            continue
        target = field.related_model.__name__
        cardinality = "||--o|" if field.one_to_one else "||--o{"
        if field.null:
            cardinality = cardinality.replace("||", "|o", 1)
        result.append((target, cardinality, model.__name__, str(field.verbose_name).replace('"', "'")))
    return result


class Command(BaseCommand):
    help = "ER-диаграммы моделей проекта в формате Mermaid (по доменам)"

    def add_arguments(self, parser):
        parser.add_argument("--output", help="Файл Markdown; без параметра — вывод в консоль")

    def handle(self, *args, **options):
        parts = [
            "# ER-диаграммы",
            "",
            "Сгенерировано из моделей Django: `python manage.py er_diagram --output docs/ER.md`.",
            "Сущности из соседних доменов показаны без полей — только чтобы были видны связи между модулями.",
            "Обозначения: `||--o{` — один ко многим, `||--o|` — один к одному, `|o` — связь необязательна (null).",
            "Поля `created_by`, `posted_by` и т. п. — автор операции (связь с `User`); линиями не показаны, чтобы не загромождать схемы.",
            "",
        ]
        for title, labels in GROUPS:
            group_models = [m for label in labels for m in apps.get_app_config(label).get_models()]
            names = {m.__name__ for m in group_models}
            lines = ["erDiagram"]
            external = set()
            for model in group_models:
                for parent, cardinality, child, label in relations(model):
                    lines.append(f'    {parent} {cardinality} {child} : "{label}"')
                    if parent not in names:
                        external.add(parent)
            for model in group_models:
                lines.append(f"    {model.__name__} {{")
                lines += [f"        {a}" for a in attributes(model)]
                lines.append("    }")
            parts += [f"## {title}", "", ", ".join(f"`{m.__name__}` — {m._meta.verbose_name}" for m in group_models), ""]
            if external:
                parts += [f"Связи с другими доменами: {', '.join(sorted(external))}.", ""]
            parts += ["```mermaid", *lines, "```", ""]

        text = "\n".join(parts)
        if options["output"]:
            Path(options["output"]).write_text(text, encoding="utf-8")
            self.stdout.write(self.style.SUCCESS(f"Записано: {options['output']}"))
        else:
            self.stdout.write(text)
