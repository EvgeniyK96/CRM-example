import pytest
from rest_framework.test import APIClient

from apps.accounts.models import Role, User
from apps.hr.models import Department, Position


@pytest.fixture
def refs(db):
    return Department.objects.create(name="Пряничный цех", is_production=True), Position.objects.create(name="Пекарь")


def employee_payload(refs, **extra):
    dep, pos = refs
    data = {"last_name": "Иванов", "first_name": "Иван", "department": dep.id, "position": pos.id, "hire_date": "2026-01-10"}
    data.update(extra)
    return data


def test_anonymous_has_no_access(db):
    assert APIClient().get("/api/hr/employees/").status_code == 401


def test_jwt_login_and_me(db):
    User.objects.create_user(username="boss", password="pass12345", role=Role.ADMIN)
    client = APIClient()
    token = client.post("/api/auth/jwt/create/", {"username": "boss", "password": "pass12345"}, format="json").data["access"]
    client.credentials(HTTP_AUTHORIZATION=f"Bearer {token}")
    me = client.get("/api/auth/users/me/")
    assert me.status_code == 200 and me.data["role"] == "admin"


def test_only_admin_manages_users(make_client):
    assert make_client(Role.HR).get("/api/accounts/users/").status_code == 403
    assert make_client(Role.ADMIN).get("/api/accounts/users/").status_code == 200


def test_admin_creates_user_with_role(admin_client):
    r = admin_client.post(
        "/api/accounts/users/", {"username": "kladov", "password": "pass12345", "role": "storekeeper"}, format="json"
    )
    assert r.status_code == 201 and User.objects.get(username="kladov").check_password("pass12345")


def test_hr_creates_employee(make_client, refs):
    r = make_client(Role.HR).post("/api/hr/employees/", employee_payload(refs), format="json")
    assert r.status_code == 201 and r.data["full_name"] == "Иванов Иван"


@pytest.mark.parametrize("role", [Role.SALES, Role.STOREKEEPER, Role.TECHNOLOGIST])
def test_other_roles_read_only_employees(make_client, refs, role):
    client = make_client(role)
    assert client.get("/api/hr/employees/").status_code == 200
    assert client.post("/api/hr/employees/", employee_payload(refs), format="json").status_code == 403


def test_fire_date_before_hire_rejected(make_client, refs):
    r = make_client(Role.HR).post("/api/hr/employees/", employee_payload(refs, fire_date="2025-01-01"), format="json")
    assert r.status_code == 400 and "fire_date" in r.data
