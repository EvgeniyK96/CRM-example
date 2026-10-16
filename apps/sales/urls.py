from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import ClientViewSet, SalesOrderViewSet

router = DefaultRouter()
router.register("clients", ClientViewSet, basename="client")
router.register("orders", SalesOrderViewSet, basename="sales-order")

urlpatterns = [path("", include(router.urls))]
