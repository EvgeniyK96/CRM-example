from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import include, path
from drf_yasg import openapi
from drf_yasg.views import get_schema_view
from rest_framework import permissions

schema_view = get_schema_view(
    openapi.Info(
        title="CRM кондитерской фабрики API",
        default_version="v1",
        description="API документация проекта",
    ),
    public=True,
    permission_classes=[permissions.AllowAny],
)

urlpatterns = [
    path("admin/", admin.site.urls),
    path("api/accounts/", include("apps.accounts.urls")),
    path("api/hr/", include("apps.hr.urls")),
    path("api/catalog/", include("apps.catalog.urls")),
    path("api/recipes/", include("apps.recipes.urls")),
    path("api/warehouse/", include("apps.warehouse.urls")),
    path("api/purchasing/", include("apps.purchasing.urls")),
    path("api/sales/", include("apps.sales.urls")),
    path("api/production/", include("apps.production.urls")),
    path("api/accounting/", include("apps.accounting.urls")),
    path("api/auth/", include("djoser.urls")),
    path("api/auth/", include("djoser.urls.jwt")),
    path("swagger/", schema_view.with_ui("swagger", cache_timeout=0), name="schema-swagger-ui"),
    path("redoc/", schema_view.with_ui("redoc", cache_timeout=0), name="schema-redoc"),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
