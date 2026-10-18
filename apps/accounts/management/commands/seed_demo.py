from django.core.management import call_command
from django.core.management.base import BaseCommand
from django.utils import timezone

from apps.accounts.models import Role, User
from apps.hr import services as hr
from apps.hr.models import Department, Employee, Position

DEMO_PASSWORD = "demo12345"

# логин, роль, имя, фамилия, подразделение, должность (None — без карточки сотрудника)
USERS = [
    ("admin", Role.ADMIN, "Администратор", "", None, None),
    ("sales", Role.SALES, "Мария", "Смирнова", "Отдел продаж", "Менеджер по продажам"),
    ("hr", Role.HR, "Ольга", "Иванова", "Отдел кадров", "Специалист по кадрам"),
    ("accountant", Role.ACCOUNTANT, "Галина", "Петрова", "Бухгалтерия", "Бухгалтер"),
    ("tech", Role.TECHNOLOGIST, "Анна", "Ли", "Технологический отдел", "Технолог"),
    ("shop_head", Role.SHOP_HEAD, "Сергей", "Кузнецов", "Производственная служба", "Начальник производства"),
    ("shop_cakes", Role.SHOP_HEAD, "Ирина", "Ахметова", "Цех тортов и пирожных", "Начальник цеха"),
    ("shop_ginger", Role.SHOP_HEAD, "Павел", "Морозов", "Пряничный цех", "Начальник цеха"),
    ("storekeeper", Role.STOREKEEPER, "Виктор", "Ким", "Склад", "Кладовщик"),
]


class Command(BaseCommand):
    help = "Полный набор учебных данных: пользователи и сотрудники, справочники, рецептуры, склад, заказы, производство"

    def add_arguments(self, parser):
        parser.add_argument(
            "--password", default=DEMO_PASSWORD,
            help="Пароль новых демо-пользователей. На публичном сервере задайте свой, а не общеизвестный demo12345",
        )

    def handle(self, *args, **options):
        password = options["password"]
        call_command("seed_hr", stdout=self.stdout)
        hire_date = timezone.localdate().replace(month=1, day=10)
        for username, role, first_name, last_name, dep, pos in USERS:
            user, created = User.objects.get_or_create(
                username=username,
                defaults={"role": role, "first_name": first_name, "last_name": last_name,
                          "is_staff": role == Role.ADMIN, "is_superuser": role == Role.ADMIN},
            )
            if created:
                user.set_password(password)
                user.save()
            if dep and not Employee.objects.filter(user=user).exists():
                employee = Employee.objects.create(
                    user=user, last_name=last_name, first_name=first_name, hire_date=hire_date,
                    department=Department.objects.get(name=dep), position=Position.objects.get(name=pos),
                )
                hr.hire(employee)
        call_command("seed_payroll", stdout=self.stdout)  # тянет за собой все модули по цепочке до зарплаты
        names = ", ".join(u for u, *_ in USERS)
        self.stdout.write(self.style.SUCCESS(f"Готово. Пользователи: {names}; пароль новых — {password}"))
