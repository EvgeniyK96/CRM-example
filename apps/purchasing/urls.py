from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import PurchaseOrderViewSet, ReceiptViewSet

router = DefaultRouter()
router.register("orders", PurchaseOrderViewSet, basename="purchase-order")
router.register("receipts", ReceiptViewSet, basename="receipt")

urlpatterns = [path("", include(router.urls))]
