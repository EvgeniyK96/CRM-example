"""
Текущий пользователь запроса — для журналов, которые пишутся в сигналах моделей (там нет request).

Выставляется JWT-аутентификацией DRF (core.authentication) и middleware для сессий (админка),
сбрасывается middleware в конце запроса. Вне запроса (команды, тесты сервисов) — None.
"""

from contextvars import ContextVar

_current_user: ContextVar = ContextVar("current_user", default=None)


def get_current_user():
    return _current_user.get()


def set_current_user(user):
    return _current_user.set(user if user is not None and user.is_authenticated else None)


class CurrentUserMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        token = set_current_user(getattr(request, "user", None))  # сессия; JWT перезапишет во вьюхе DRF
        try:
            return self.get_response(request)
        finally:
            _current_user.reset(token)
