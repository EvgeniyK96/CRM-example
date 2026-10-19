from rest_framework_simplejwt.authentication import JWTAuthentication as BaseJWTAuthentication

from .current_user import set_current_user


class JWTAuthentication(BaseJWTAuthentication):
    """JWT SimpleJWT + запоминает пользователя для журналов в сигналах (core.current_user)."""

    def authenticate(self, request):
        result = super().authenticate(request)
        if result is not None:
            set_current_user(result[0])
        return result
