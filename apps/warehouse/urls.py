from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import LotViewSet, StockMoveViewSet, StockViewSet

router = DefaultRouter()
router.register("lots", LotViewSet, basename="lot")
router.register("stock", StockViewSet, basename="stock")
router.register("moves", StockMoveViewSet, basename="move")

urlpatterns = [path("", include(router.urls))]
