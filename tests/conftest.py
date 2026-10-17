import pytest
from rest_framework.test import APIClient

from apps.accounts.models import Role, User


@pytest.fixture
def make_client(db):
    def _make(role):
        """Клиент API от имени пользователя с ролью; повторный вызов с той же ролью — тот же пользователь."""
        user = User.objects.filter(username=f"u_{role}").first() or User.objects.create_user(
            username=f"u_{role}", password="pass12345", role=role
        )
        client = APIClient()
        client.force_authenticate(user)
        return client

    return _make


@pytest.fixture
def admin_client(make_client):
    return make_client(Role.ADMIN)
