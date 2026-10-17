from django.urls import include, path
from rest_framework.routers import DefaultRouter

from . import views

router = DefaultRouter()
router.register("departments", views.DepartmentViewSet, basename="department")
router.register("positions", views.PositionViewSet, basename="position")
router.register("employees", views.EmployeeViewSet, basename="employee")
router.register("orders", views.HROrderViewSet, basename="hr-order")
router.register("absences", views.AbsenceViewSet, basename="absence")
router.register("holidays", views.HolidayViewSet, basename="holiday")

urlpatterns = [
    path("timesheet/", views.TimesheetView.as_view(), name="timesheet"),
    path("", include(router.urls)),
]
