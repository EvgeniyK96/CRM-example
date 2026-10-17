from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import ClientViewSet, SalesOrderViewSet, ShipmentViewSet

router = DefaultRouter()
router.register("clients", ClientViewSet, basename="client")
router.register("orders", SalesOrderViewSet, basename="sales-order")
router.register("shipments", ShipmentViewSet, basename="shipment")

urlpatterns = [path("", include(router.urls))]
