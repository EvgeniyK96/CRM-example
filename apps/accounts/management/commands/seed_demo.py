from django.core.management import call_command
from django.core.management.base import BaseCommand

from apps.accounts.models import Role, User

DEMO_PASSWORD = "demo12345"

USERS = [
    ("admin", Role.ADMIN, "Администратор"),
    ("sales", Role.SALES, "Мария"),
    ("hr", Role.HR, "Ольга"),
    ("accountant", Role.ACCOUNTANT, "Галина"),
    ("tech", Role.TECHNOLOGIST, "Анна"),
    ("shop_head", Role.SHOP_HEAD, "Сергей"),
    ("storekeeper", Role.STOREKEEPER, "Виктор"),
]


class Command(BaseCommand):
    help = "Полный набор учебных данных: пользователи всех ролей, справочники, рецептуры, остатки"

    def handle(self, *args, **options):
        for username, role, first_name in USERS:
            user, created = User.objects.get_or_create(
                username=username,
                defaults={"role": role, "first_name": first_name, "is_staff": role == Role.ADMIN,
                          "is_superuser": role == Role.ADMIN},
            )
            if created:
                user.set_password(DEMO_PASSWORD)
                user.save()
        call_command("seed_sales", stdout=self.stdout)  # тянет за собой рецептуры, каталог и закупки
        self.stdout.write(self.style.SUCCESS(f"Готово. Пользователи: {', '.join(u for u, *_ in USERS)}; пароль {DEMO_PASSWORD}"))
