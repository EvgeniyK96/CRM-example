from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import DepartmentViewSet, EmployeeViewSet, PositionViewSet

router = DefaultRouter()
router.register("departments", DepartmentViewSet, basename="department")
router.register("positions", PositionViewSet, basename="position")
router.register("employees", EmployeeViewSet, basename="employee")

urlpatterns = [path("", include(router.urls))]
