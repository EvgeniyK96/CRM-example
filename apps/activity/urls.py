from rest_framework.routers import SimpleRouter

from .views import ActivityViewSet, NotificationViewSet

router = SimpleRouter()
# notifications/ — раньше пустого префикса, иначе «notifications» примут за id записи ленты
router.register("notifications", NotificationViewSet, basename="notification")
router.register("", ActivityViewSet, basename="activity")

urlpatterns = router.urls
