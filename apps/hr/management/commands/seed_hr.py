from django.core.management.base import BaseCommand
from django.utils import timezone

from apps.hr.models import Department, Employee, Position

DEPARTMENTS = [
    ("Цех тортов и пирожных", True),
    ("Пряничный цех", True),
    ("Вафельный цех", True),
    ("Сдобный цех", True),
    ("Склад", False),
    ("Отдел продаж", False),
    ("Бухгалтерия", False),
    ("Отдел кадров", False),
    ("Технологический отдел", False),
    ("Производственная служба", False),
]
POSITIONS = [
    ("Начальник цеха", 450000),
    ("Технолог", 400000),
    ("Кондитер", 300000),
    ("Пекарь", 280000),
    ("Упаковщик", 220000),
    ("Кладовщик", 260000),
    ("Менеджер по продажам", 320000),
    ("Бухгалтер", 350000),
    ("Специалист по кадрам", 300000),
    ("Начальник производства", 550000),
]

# Рабочие цехов (без учётных записей); ФИО вымышленные
WORKERS = [
    ("Ким", "Алина", "Цех тортов и пирожных", "Кондитер"),
    ("Жуматова", "Айгерим", "Цех тортов и пирожных", "Кондитер"),
    ("Волков", "Денис", "Пряничный цех", "Пекарь"),
    ("Сериков", "Ерлан", "Пряничный цех", "Пекарь"),
    ("Орлова", "Наталья", "Вафельный цех", "Кондитер"),
    ("Нурланов", "Асхат", "Вафельный цех", "Упаковщик"),
    ("Белова", "Ксения", "Сдобный цех", "Пекарь"),
    ("Тимуров", "Рустам", "Сдобный цех", "Пекарь"),
]


class Command(BaseCommand):
    help = "Заполняет цеха, подразделения и должности"

    def handle(self, *args, **options):
        for name, prod in DEPARTMENTS:
            Department.objects.get_or_create(name=name, defaults={"is_production": prod})
        for name, salary in POSITIONS:
            Position.objects.get_or_create(name=name, defaults={"base_salary": salary})
        hire_date = timezone.localdate().replace(month=1, day=10)
        for last, first, dep, pos in WORKERS:
            Employee.objects.get_or_create(last_name=last, first_name=first, defaults={
                "department": Department.objects.get(name=dep), "position": Position.objects.get(name=pos),
                "hire_date": hire_date,
            })
        self.stdout.write(self.style.SUCCESS("Справочники HR заполнены"))
