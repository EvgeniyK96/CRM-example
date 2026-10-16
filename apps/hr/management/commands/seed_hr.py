from django.core.management.base import BaseCommand

from apps.hr.models import Department, Position

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
]


class Command(BaseCommand):
    help = "Заполняет цеха, подразделения и должности"

    def handle(self, *args, **options):
        for name, prod in DEPARTMENTS:
            Department.objects.get_or_create(name=name, defaults={"is_production": prod})
        for name, salary in POSITIONS:
            Position.objects.get_or_create(name=name, defaults={"base_salary": salary})
        self.stdout.write(self.style.SUCCESS("Справочники HR заполнены"))
