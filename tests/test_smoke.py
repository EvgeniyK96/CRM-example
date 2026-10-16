import pytest


@pytest.mark.django_db
def test_swagger_ui(client):
    response = client.get("/swagger/")
    assert response.status_code == 200


@pytest.mark.django_db
def test_redoc_ui(client):
    response = client.get("/redoc/")
    assert response.status_code == 200


@pytest.mark.django_db
def test_jwt_create_endpoint_exists(client):
    response = client.post("/api/auth/jwt/create/", data={}, content_type="application/json")
    assert response.status_code != 404


@pytest.mark.django_db
def test_admin_redirect(client):
    response = client.get("/admin/")
    assert response.status_code in (200, 302)
