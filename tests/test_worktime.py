from datetime import datetime, time, timedelta

import pytest
from django.utils import timezone

from apps.accounts.models import Role, User
from apps.hr import worktime
from apps.hr.models import WorkDay

URL = "/api/hr/workdays/"
TODAY = timezone.localdate()


def at(hour, minute=0, day=TODAY):
    return timezone.make_aware(datetime.combine(day, time(hour, minute)))


@pytest.fixture
def user(make_client):
    make_client(Role.SALES)
    return User.objects.get(username="u_sales")


def test_day_with_pause(user):
    worktime.start(user, now=at(8, 50))
    worktime.pause(user, now=at(12))
    worktime.start(user, now=at(13))
    s = worktime.summary(worktime.today(user, now=at(15)), now=at(15))
    assert s["status"] == "working" and not s["late"]
    assert s["worked_seconds"] == (3 * 60 + 10 + 2 * 60) * 60 and s["break_seconds"] == 3600

    worktime.finish(user, " Отгрузили три заказа ", now=at(18))
    s = worktime.summary(worktime.today(user, now=at(18)), now=at(20))  # после завершения время не идёт
    assert s["status"] == "finished" and s["worked_seconds"] == (3 * 60 + 10 + 5 * 60) * 60
    assert s["report"] == "Отгрузили три заказа"


def test_late_start_and_reopen_finished_day(user):
    worktime.start(user, now=at(9, 15))
    worktime.finish(user, now=at(10))
    worktime.start(user, now=at(11))  # вернулся к завершённому дню
    s = worktime.summary(worktime.today(user, now=at(12)), now=at(12))
    assert s["late"] and s["status"] == "working" and s["finished_at"] is None
    assert WorkDay.objects.count() == 1


def test_rules(user):
    with pytest.raises(worktime.WorkTimeError):
        worktime.pause(user, now=at(9))
    with pytest.raises(worktime.WorkTimeError):
        worktime.finish(user, now=at(9))
    worktime.start(user, now=at(9))
    with pytest.raises(worktime.WorkTimeError):
        worktime.start(user, now=at(9, 5))


def test_forgotten_day_closed_by_norm(user):
    yesterday = TODAY - timedelta(days=1)
    worktime.start(user, now=at(9, day=yesterday))
    worktime.start(user, now=at(9))
    old = WorkDay.objects.get(date=yesterday)
    assert old.auto_closed and old.finished_at == at(17, day=yesterday)  # 9:00 + 8 ч нормы
    assert worktime.summary(old)["worked_seconds"] == 8 * 3600


def test_api_buttons_and_visibility(make_client):
    sales, store, hr = make_client(Role.SALES), make_client(Role.STOREKEEPER), make_client(Role.HR)
    assert sales.get(f"{URL}current/").data["status"] == "none"
    assert sales.post(f"{URL}start/").data["status"] == "working"
    assert sales.post(f"{URL}start/").status_code == 400
    assert sales.post(f"{URL}pause/").data["status"] == "paused"
    assert sales.post(f"{URL}finish/", {"report": "готово"}).data["status"] == "finished"
    store.post(f"{URL}start/")

    assert len(sales.get(URL).data["results"]) == 1  # только свой день
    rows = hr.get(URL, {"date_from": TODAY, "date_to": TODAY}).data["results"]
    assert {r["user_name"] for r in rows} == {"u_sales", "u_storekeeper"}
    assert {r["status"] for r in rows} == {"finished", "working"}
