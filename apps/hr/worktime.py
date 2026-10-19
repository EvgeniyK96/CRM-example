"""
Учёт рабочего дня: начать / пауза / продолжить / завершить.

Отработано — сумма интервалов работы, перерывы — промежутки между ними. Опоздание — начало дня позже
WORKDAY_START. Незавершённый день закрывается сам, когда сотрудник начинает следующий: конец ставится
по норме (начало + WORKDAY_HOURS, но не позже конца того дня), день помечается auto_closed — отдел кадров
видит, что время оценочное.
"""

from datetime import datetime, time, timedelta

from django.conf import settings
from django.db import transaction
from django.utils import timezone

from core.exceptions import DomainError

from .models import WorkDay, WorkInterval


class WorkTimeError(DomainError):
    pass


NONE, WORKING, PAUSED, FINISHED = "none", "working", "paused", "finished"


def _day_end(day) -> datetime:
    return timezone.make_aware(datetime.combine(day.date, time.max))


def _workday_start(on_date) -> datetime:
    h, m = (int(x) for x in settings.WORKDAY_START.split(":"))
    return timezone.make_aware(datetime.combine(on_date, time(h, m)))


def _intervals(day) -> list[WorkInterval]:
    # prefetch_related("intervals") в списках; в действиях — свежий запрос
    return list(day.intervals.all())


def status(day: WorkDay | None) -> str:
    if day is None or not _intervals(day):
        return NONE
    if day.finished_at:
        return FINISHED
    return WORKING if _intervals(day)[-1].ended_at is None else PAUSED


def summary(day: WorkDay | None, now=None) -> dict:
    """Состояние дня для шапки и отчёта; открытый интервал считается до now."""
    now = now or timezone.now()
    intervals = _intervals(day) if day else []
    worked = sum(((i.ended_at or now) - i.started_at for i in intervals), timedelta())
    first = intervals[0].started_at if intervals else None
    last = (intervals[-1].ended_at or now) if intervals else None
    norm = timedelta(hours=float(settings.WORKDAY_HOURS))
    return {
        "id": day.pk if day else None,
        "date": day.date if day else timezone.localdate(now),
        "status": status(day),
        "started_at": first,
        "finished_at": day.finished_at if day else None,
        "worked_seconds": int(worked.total_seconds()),
        "break_seconds": int(((last - first) - worked).total_seconds()) if first else 0,
        "norm_seconds": int(norm.total_seconds()),
        "late": bool(first and first > _workday_start(day.date)),
        "auto_closed": bool(day and day.auto_closed),
        "report": day.report if day else "",
        "intervals": [{"started_at": i.started_at, "ended_at": i.ended_at} for i in intervals],
    }


def today(user, now=None) -> WorkDay | None:
    on_date = timezone.localdate(now or timezone.now())
    return WorkDay.objects.filter(user=user, date=on_date).prefetch_related("intervals").first()


def _close_forgotten(user, on_date):
    norm = timedelta(hours=float(settings.WORKDAY_HOURS))
    for day in WorkDay.objects.select_for_update().filter(user=user, date__lt=on_date, finished_at=None):
        intervals = list(day.intervals.all())
        open_ = next((i for i in intervals if i.ended_at is None), None)
        if open_:
            open_.ended_at = min(_day_end(day), max(open_.started_at, intervals[0].started_at + norm))
            open_.save(update_fields=["ended_at"])
            end = open_.ended_at
        else:
            end = intervals[-1].ended_at if intervals else _day_end(day)
        day.finished_at, day.auto_closed = end, True
        day.save(update_fields=["finished_at", "auto_closed"])


def _today_locked(user, now) -> WorkDay | None:
    return WorkDay.objects.select_for_update().filter(user=user, date=timezone.localdate(now)).first()


@transaction.atomic
def start(user, now=None) -> WorkDay:
    """Начать день, продолжить после паузы или вернуться к завершённому дню."""
    now = now or timezone.now()
    _close_forgotten(user, timezone.localdate(now))
    day = _today_locked(user, now) or WorkDay.objects.create(user=user, date=timezone.localdate(now))
    if day.intervals.filter(ended_at=None).exists():
        raise WorkTimeError("Рабочий день уже идёт.")
    if day.finished_at:
        day.finished_at = None
        day.save(update_fields=["finished_at"])
    WorkInterval.objects.create(day=day, started_at=now)
    return day


@transaction.atomic
def pause(user, now=None) -> WorkDay:
    now = now or timezone.now()
    day = _today_locked(user, now)
    updated = day and day.intervals.filter(ended_at=None).update(ended_at=now)
    if not updated:
        raise WorkTimeError("Поставить на паузу можно только идущий рабочий день.")
    return day


@transaction.atomic
def finish(user, report: str = "", now=None) -> WorkDay:
    now = now or timezone.now()
    day = _today_locked(user, now)
    if day is None or not day.intervals.exists():
        raise WorkTimeError("Рабочий день ещё не начат.")
    if day.finished_at:
        raise WorkTimeError("Рабочий день уже завершён.")
    day.intervals.filter(ended_at=None).update(ended_at=now)
    day.finished_at, day.report = now, report.strip()
    day.save(update_fields=["finished_at", "report"])
    return day
