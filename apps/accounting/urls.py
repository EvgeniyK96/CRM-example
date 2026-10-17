from django.urls import include, path
from rest_framework.routers import DefaultRouter

from . import views

router = DefaultRouter()
router.register("accounts", views.AccountViewSet, basename="account")
router.register("entries", views.JournalEntryViewSet, basename="journal-entry")
router.register("invoices", views.InvoiceViewSet, basename="invoice")
router.register("payments", views.PaymentViewSet, basename="payment")

urlpatterns = [
    path("reports/trial-balance/", views.TrialBalanceView.as_view()),
    path("reports/account-card/", views.AccountCardView.as_view()),
    path("reports/receivables/", views.ReceivablesView.as_view()),
    path("reports/payables/", views.PayablesView.as_view()),
    path("reports/profit-loss/", views.ProfitLossView.as_view()),
    path("", include(router.urls)),
]
