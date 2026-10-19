import random
from datetime import datetime, time, timedelta

from django.core.management.base import BaseCommand
from django.utils import timezone

from apps.hr.models import Employee, Holiday, WorkDay, WorkInterval

REPORTS = [
    "Планёрка, текущие задачи закрыты",
    "Работа с документами, сверка с бухгалтерией",
    "Обзвон клиентов, уточнение заказов на неделю",
    "",
    "",
]


def at(day, hour, minute):
    return timezone.make_aware(datetime.combine(day, time(hour, minute)))


class Command(BaseCommand):
    help = "Учёт рабочего дня: рабочие дни сотрудников с учётными записями за последние две недели (повторно не создаёт)"

    def handle(self, *args, **options):
        today = timezone.localdate()
        days = [today - timedelta(days=n) for n in range(14, 0, -1)]
        holidays = set(Holiday.objects.filter(date__in=days).values_list("date", flat=True))
        workdays = [d for d in days if d.weekday() < 5 and d not in holidays]
        created = 0
        for employee in Employee.objects.exclude(user=None).select_related("user"):
            user = employee.user
            if WorkDay.objects.filter(user=user, date__lt=today).exists():
                continue
            rnd = random.Random(user.pk)  # одинаковые данные при каждом запуске на чистой базе
            for i, day in enumerate(workdays):
                start = at(day, 8, 40) + timedelta(minutes=rnd.randint(0, 40))  # с 9:00 — опоздание
                lunch = at(day, 12, 30) + timedelta(minutes=rnd.randint(0, 30))
                back = lunch + timedelta(minutes=rnd.randint(40, 65))
                end = at(day, 17, 40) + timedelta(minutes=rnd.randint(0, 50))
                forgot = i == len(workdays) - 3 and rnd.random() < 0.5  # кто-то забыл завершить день
                wd = WorkDay.objects.create(
                    user=user, date=day, finished_at=end, auto_closed=forgot,
                    report="" if forgot else rnd.choice(REPORTS),
                )
                WorkInterval.objects.bulk_create([
                    WorkInterval(day=wd, started_at=start, ended_at=lunch),
                    WorkInterval(day=wd, started_at=back, ended_at=end),
                ])
                created += 1
        self.stdout.write(f"Учёт рабочего дня: создано дней — {created}")
