from django.db.models import ProtectedError, RestrictedError
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import exception_handler as drf_exception_handler


class DomainError(Exception):
    """Нарушение бизнес-правила. API отвечает 400 с текстом ошибки."""


def exception_handler(exc, context):
    if isinstance(exc, DomainError):
        return Response({"detail": str(exc)}, status=status.HTTP_400_BAD_REQUEST)
    if isinstance(exc, (ProtectedError, RestrictedError)):
        # Удаление записи, на которую ссылаются документы (on_delete=PROTECT): 400 вместо 500
        return Response(
            {"detail": "Нельзя удалить: запись используется в других документах. Сделайте её неактивной."},
            status=status.HTTP_400_BAD_REQUEST,
        )
    return drf_exception_handler(exc, context)
