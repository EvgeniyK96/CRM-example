from datetime import date
from decimal import Decimal

import pytest
from rest_framework.test import APIClient

from apps.accounting import chart as C
from apps.accounting.models import JournalEntry, Posting
from apps.accounts.models import Role, User
from apps.hr import services as hr
from apps.hr.models import Absence, Department, Employee, Holiday, HROrder, Position
from apps.payroll import services as payroll
from apps.payroll.models import PayrollPeriod

D = Decimal
# Сентябрь 2026: 30 дней, начинается во вторник, 22 рабочих дня (без праздников)
YEAR, MONTH = 2026, 9


@pytest.fixture
def staff(db):
    shop = Department.objects.create(name="Цех", is_production=True)
    office = Department.objects.create(name="Бухгалтерия")
    baker = Position.objects.create(name="Пекарь", base_salary=220000)
    clerk = Position.objects.create(name="Бухгалтер", base_salary=400000)
    return {
        "shop": shop, "office": office, "baker": baker, "clerk": clerk,
        "anna": Employee.objects.create(last_name="Анна", first_name="А", department=shop, position=baker,
                                        hire_date=date(2026, 1, 10)),
        "boris": Employee.objects.create(last_name="Борис", first_name="Б", department=office, position=clerk,
                                         hire_date=date(2026, 1, 10)),
    }


def absence(employee, kind, d1, d2):
    return Absence.objects.create(employee=employee, kind=kind, date_from=date(YEAR, MONTH, d1), date_to=date(YEAR, MONTH, d2))


# --- Кадры -------------------------------------------------------------------


def test_salary_defaults_to_position(staff):
    assert staff["anna"].salary == 220000


def test_create_employee_issues_hire_order(make_client, staff):
    api = make_client(Role.HR)
    r = api.post("/api/hr/employees/", {"last_name": "Новый", "first_name": "Н", "department": staff["shop"].pk,
                                        "position": staff["baker"].pk, "hire_date": "2026-10-01"}, format="json")
    assert r.status_code == 201 and D(r.data["salary"]) == 220000
    order = HROrder.objects.get(employee_id=r.data["id"])
    assert (order.kind, order.number[:3]) == ("hire", "ПК-")


def test_order_fields_change_only_by_order(make_client, staff):
    api = make_client(Role.HR)
    url = f"/api/hr/employees/{staff['anna'].pk}/"
    r = api.patch(url, {"salary": "1"}, format="json")
    assert r.status_code == 400 and "salary" in r.data
    assert api.patch(url, {"phone": "+7 700"}, format="json").status_code == 200


def test_transfer_salary_and_dismissal_orders(make_client, staff):
    api = make_client(Role.HR)
    anna = staff["anna"]
    r = api.post("/api/hr/orders/", {"kind": "transfer", "employee": anna.pk, "date": "2026-09-01",
                                     "to_department": staff["office"].pk, "reason": "Перевод"}, format="json")
    assert r.status_code == 201, r.data
    assert (r.data["from_department_name"], r.data["to_department_name"]) == ("Цех", "Бухгалтерия")

    api.post("/api/hr/orders/", {"kind": "salary", "employee": anna.pk, "date": "2026-09-01", "to_salary": "250000"},
             format="json")
    anna.refresh_from_db()
    assert (anna.department, anna.salary) == (staff["office"], 250000)

    user = User.objects.create_user(username="anna", password="x", role=Role.SALES)
    anna.user = user
    anna.save()
    api.post("/api/hr/orders/", {"kind": "dismissal", "employee": anna.pk, "date": "2026-09-30"}, format="json")
    anna.refresh_from_db()
    user.refresh_from_db()
    assert (anna.status, anna.fire_date, user.is_active) == ("fired", date(2026, 9, 30), False)
    r = api.post("/api/hr/orders/", {"kind": "salary", "employee": anna.pk, "date": "2026-10-01", "to_salary": "1"},
                 format="json")
    assert r.status_code == 400  # уволенному приказы не оформляются


def test_hire_order_not_allowed_directly(make_client, staff):
    r = make_client(Role.HR).post("/api/hr/orders/", {"kind": "hire", "employee": staff["anna"].pk, "date": "2026-09-01"},
                                  format="json")
    assert r.status_code == 400


def test_absence_validation(make_client, staff):
    api = make_client(Role.HR)
    base = {"employee": staff["anna"].pk, "kind": "vacation"}
    assert api.post("/api/hr/absences/", {**base, "date_from": "2026-09-01", "date_to": "2026-09-10"}, format="json").status_code == 201
    overlap = api.post("/api/hr/absences/", {**base, "kind": "sick", "date_from": "2026-09-10", "date_to": "2026-09-12"}, format="json")
    assert overlap.status_code == 400 and "Пересекается" in overlap.data["detail"]
    before_hire = api.post("/api/hr/absences/", {**base, "date_from": "2025-12-01", "date_to": "2025-12-02"}, format="json")
    assert before_hire.status_code == 400


def test_timesheet_codes_and_counts(staff):
    Holiday.objects.create(date=date(YEAR, MONTH, 1), name="Тестовый праздник")  # вторник
    anna = staff["anna"]
    absence(anna, "vacation", 7, 13)       # пн–вс: 7 календарных дней, включая выходные
    absence(anna, "sick", 14, 15)          # 2 рабочих дня
    absence(anna, "business_trip", 16, 16)  # считается отработанным
    absence(anna, "unpaid", 17, 17)

    sheet = hr.timesheet(YEAR, MONTH)
    row = next(r for r in sheet["rows"] if r["employee"] == anna.pk)
    assert sheet["norm_days"] == 21  # 22 − праздник
    assert row["cells"][0] == "В" and row["cells"][6:13] == ["О"] * 7 and row["cells"][13:17] == ["Б", "Б", "К", "НН"]
    assert (row["vacation_days"], row["sick_days"], row["unpaid_days"]) == (7, 2, 1)
    assert row["worked_days"] == 21 - 5 - 2 - 1  # норма − рабочие дни отпуска (7–11) − больничный − без содержания


def test_timesheet_respects_hire_and_fire_dates(staff):
    late = Employee.objects.create(last_name="Поздний", first_name="П", department=staff["shop"],
                                   position=staff["baker"], hire_date=date(YEAR, MONTH, 28))
    row = next(r for r in hr.timesheet(YEAR, MONTH)["rows"] if r["employee"] == late.pk)
    assert row["cells"][:27] == [""] * 27 and row["worked_days"] == 3  # 28, 29, 30 сентября


# --- Зарплата ----------------------------------------------------------------


def period():
    p = PayrollPeriod.objects.create(year=YEAR, month=MONTH)
    payroll.calculate(p)
    return p


def test_full_month_payslip(staff):
    slip = period().payslips.get(employee=staff["boris"])  # оклад 400 000, полный месяц
    lines = {line.rate.code: line.amount for line in slip.lines.all()}
    assert (slip.norm_days, slip.worked_days, slip.gross) == (22, 22, 400000)
    assert lines["OPV"] == 40000 and lines["VOSMS"] == 8000
    assert lines["IPN"] == D("29145.00")  # (400000 − 40000 − 8000 − 60550) × 10%
    assert slip.withheld == 77145 and slip.net == 322855
    assert slip.employer_total == 400000 * D("0.105")  # СО 5% + ООСМС 3% + ОПВР 2.5%


def test_vacation_and_sick_pay(staff):
    absence(staff["anna"], "vacation", 1, 14)  # 14 календарных, из них 10 рабочих
    absence(staff["anna"], "sick", 15, 16)     # 2 рабочих
    slip = period().payslips.get(employee=staff["anna"])
    assert (slip.worked_days, slip.vacation_days, slip.sick_days) == (10, 14, 2)
    assert slip.salary_accrued == D("100000.00")              # 220000 × 10/22
    assert slip.vacation_pay == D("105119.45")                # 220000 / 29.3 × 14
    assert slip.sick_pay == D("20000.00")                     # 220000 × 2/22
    assert slip.gross == slip.salary_accrued + slip.vacation_pay + slip.sick_pay


def test_low_salary_has_no_negative_tax(staff):
    staff["anna"].salary = 50000
    staff["anna"].save()
    slip = period().payslips.get(employee=staff["anna"])
    assert next(line for line in slip.lines.all() if line.rate.code == "IPN").amount == 0


def test_bonus_survives_recalculation(make_client, staff):
    p = period()
    api = make_client(Role.ACCOUNTANT)
    slip = p.payslips.get(employee=staff["anna"])
    r = api.patch(f"/api/payroll/payslips/{slip.pk}/", {"bonus": "30000"}, format="json")
    assert r.status_code == 200 and D(r.data["gross"]) == 250000
    api.post(f"/api/payroll/periods/{p.pk}/calculate/")
    assert p.payslips.get(employee=staff["anna"]).bonus == 30000


def test_post_pay_and_unpost(make_client, staff):
    api = make_client(Role.ACCOUNTANT)
    p = period()
    assert api.post(f"/api/payroll/periods/{p.pk}/post/").data["status"] == "posted"

    def credit(code):
        return sum(x.amount for x in Posting.objects.filter(credit__code=code)) - sum(
            x.amount for x in Posting.objects.filter(debit__code=code))

    assert credit(C.PAYROLL) == sum(s.net for s in p.payslips.all())  # начислено − удержано
    expense = {code: sum(x.amount for x in Posting.objects.filter(debit__code=code)) for code in (C.PRODUCTION_LABOR, C.ADMIN_EXPENSES)}
    anna, boris = p.payslips.get(employee=staff["anna"]), p.payslips.get(employee=staff["boris"])
    assert expense[C.PRODUCTION_LABOR] == anna.gross + anna.employer_total  # цех — 7110
    assert expense[C.ADMIN_EXPENSES] == boris.gross + boris.employer_total  # офис — 7210
    assert api.patch(f"/api/payroll/payslips/{anna.pk}/", {"bonus": "1"}, format="json").status_code == 400

    assert api.post(f"/api/payroll/periods/{p.pk}/unpost/").data["status"] == "draft"
    assert not JournalEntry.objects.filter(source_type="payroll").exists()

    api.post(f"/api/payroll/periods/{p.pk}/post/")
    assert api.post(f"/api/payroll/periods/{p.pk}/pay/", {"method": "bank"}, format="json").data["status"] == "paid"
    assert credit(C.PAYROLL) == 0
    assert api.post(f"/api/payroll/periods/{p.pk}/unpost/").status_code == 400


def test_period_validation_and_permissions(make_client, staff):
    api = make_client(Role.ACCOUNTANT)
    assert api.post("/api/payroll/periods/", {"year": 2099, "month": 1}, format="json").status_code == 400
    r = api.post("/api/payroll/periods/", {"year": YEAR, "month": MONTH}, format="json")
    assert r.status_code == 201 and r.data["totals"]["employees"] == 2
    assert api.post("/api/payroll/periods/", {"year": YEAR, "month": MONTH}, format="json").status_code == 400
    assert make_client(Role.HR).get("/api/payroll/periods/").status_code == 403
    assert make_client(Role.HR).get("/api/payroll/rates/").status_code == 200


def test_my_payslips_only_own_and_posted(staff):
    user = User.objects.create_user(username="boris", password="x", role=Role.SALES)
    staff["boris"].user = user
    staff["boris"].save()
    p = period()
    api = APIClient()
    api.force_authenticate(user)
    assert api.get("/api/payroll/my-payslips/").data == []  # черновик не виден
    payroll.post(p)
    slips = api.get("/api/payroll/my-payslips/").data
    assert [s["employee_name"] for s in slips] == ["Борис Б"]


def test_seed_demo_payroll(db):
    from django.core.management import call_command

    call_command("seed_demo")
    statuses = set(PayrollPeriod.objects.values_list("status", flat=True))
    assert statuses == {"paid", "draft"}
