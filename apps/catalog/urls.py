from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import CategoryViewSet, ItemViewSet, SupplierViewSet, UnitViewSet

router = DefaultRouter()
router.register("units", UnitViewSet, basename="unit")
router.register("categories", CategoryViewSet, basename="category")
router.register("items", ItemViewSet, basename="item")
router.register("suppliers", SupplierViewSet, basename="supplier")

urlpatterns = [path("", include(router.urls))]
