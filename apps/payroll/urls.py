from django.urls import include, path
from rest_framework.routers import DefaultRouter

from . import views

router = DefaultRouter()
router.register("rates", views.PayrollRateViewSet, basename="payroll-rate")
router.register("periods", views.PayrollPeriodViewSet, basename="payroll-period")
router.register("payslips", views.PayslipViewSet, basename="payslip")
router.register("my-payslips", views.MyPayslipViewSet, basename="my-payslip")

urlpatterns = [path("", include(router.urls))]
