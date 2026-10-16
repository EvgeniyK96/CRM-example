from rest_framework import viewsets

from .models import User
from .permissions import HasRole
from .serializers import UserAdminSerializer


class UserViewSet(viewsets.ModelViewSet):
    """Управление пользователями — только администратор."""

    queryset = User.objects.order_by("username")
    serializer_class = UserAdminSerializer
    permission_classes = [HasRole()]
    filterset_fields = ["role", "is_active"]
    search_fields = ["username", "first_name", "last_name", "email"]

