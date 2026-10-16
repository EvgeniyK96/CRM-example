from rest_framework.permissions import SAFE_METHODS, BasePermission

from .models import Role


def has_role(user, *roles):
    return bool(user and user.is_authenticated and (user.role == Role.ADMIN or user.role in roles))


def HasRole(*roles):
    """Фабрика permission-класса: доступ ролям из списка и администратору."""

    class _HasRole(BasePermission):
        def has_permission(self, request, view):
            return has_role(request.user, *roles)

    _HasRole.__name__ = "HasRole_" + "_".join(roles)
    return _HasRole


def ReadAnyWriteRoles(*roles):
    """Читать может любой авторизованный, изменять — только указанные роли и админ."""

    class _ReadAnyWriteRoles(BasePermission):
        def has_permission(self, request, view):
            if not (request.user and request.user.is_authenticated):
                return False
            if request.method in SAFE_METHODS:
                return True
            return has_role(request.user, *roles)

    _ReadAnyWriteRoles.__name__ = "ReadAnyWriteRoles_" + "_".join(roles)
    return _ReadAnyWriteRoles
