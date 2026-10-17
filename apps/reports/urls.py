from django.urls import path

from . import views

urlpatterns = [
    path("dashboard/", views.DashboardView.as_view(), name="dashboard"),
    path("sales/", views.SalesReportView.as_view(), name="report-sales"),
    path("production/", views.ProductionReportView.as_view(), name="report-production"),
    path("stock/", views.StockReportView.as_view(), name="report-stock"),
]
