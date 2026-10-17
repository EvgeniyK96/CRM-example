from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import DemandView, ProductionTaskViewSet, TraceView

router = DefaultRouter()
router.register("tasks", ProductionTaskViewSet, basename="production-task")

urlpatterns = [
    path("demand/", DemandView.as_view(), name="production-demand"),
    path("trace/<int:lot_id>/", TraceView.as_view(), name="lot-trace"),
    path("", include(router.urls)),
]
