from datetime import date
from decimal import Decimal

from django.core.management import call_command
from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils import timezone

from apps.accounts.models import User
from apps.hr import services as hr
from apps.hr.models import Absence, Department, Employee, HROrder
from apps.payroll import services
from apps.payroll.models import PayrollPeriod


class Command(BaseCommand):
    help = "Кадровые события (отпуск, больничный, приказы) и зарплата: прошлый месяц выплачен, текущий — черновик"

    @transaction.atomic
    def handle(self, *args, **options):
        call_command("seed_accounting", stdout=self.stdout)
        if PayrollPeriod.objects.exists():
            self.stdout.write("Ведомости уже есть — пропускаю")
            return

        hr_user = User.objects.filter(role="hr").first()
        accountant = User.objects.filter(role="accountant").first()
        year, month = hr.previous_month(timezone.localdate())

        def worker(last_name, first_name):
            return Employee.objects.get(last_name=last_name, first_name=first_name)

        # Отсутствия в прошлом месяце
        Absence.objects.create(employee=worker("Ким", "Алина"), kind="vacation", date_from=date(year, month, 1),
                               date_to=date(year, month, 14), comment="Ежегодный отпуск", created_by=hr_user)
        Absence.objects.create(employee=worker("Волков", "Денис"), kind="sick", date_from=date(year, month, 15),
                               date_to=date(year, month, 17), comment="Больничный лист", created_by=hr_user)
        Absence.objects.create(employee=worker("Орлова", "Наталья"), kind="business_trip", date_from=date(year, month, 21),
                               date_to=date(year, month, 23), comment="Обучение у поставщика оборудования",
                               created_by=hr_user)

        # Приказы: повышение оклада и перевод
        hr.issue_order(worker("Сериков", "Ерлан"), HROrder.Kind.SALARY, date(year, month, 1), salary=Decimal(310000),
                       reason="По итогам аттестации", user=hr_user)
        hr.issue_order(worker("Тимуров", "Рустам"), HROrder.Kind.TRANSFER, date(year, month, 1),
                       department=Department.objects.get(name="Пряничный цех"), reason="Производственная необходимость",
                       user=hr_user)

        # Прошлый месяц: рассчитана, премия кондитеру, проведена, выплачена
        past = PayrollPeriod.objects.create(year=year, month=month, created_by=accountant)
        services.calculate(past)
        services.set_bonus(past.payslips.get(employee=worker("Жуматова", "Айгерим")), Decimal(30000))
        services.post(past, accountant)
        services.pay(past, user=accountant)

        # Текущий месяц — черновик для экспериментов
        today = timezone.localdate()
        services.calculate(PayrollPeriod.objects.create(year=today.year, month=today.month, created_by=accountant))
        self.stdout.write(self.style.SUCCESS(f"Зарплата за {month:02d}.{year} выплачена, текущий месяц — черновик"))
