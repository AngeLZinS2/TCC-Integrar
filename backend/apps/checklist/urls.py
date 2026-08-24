from rest_framework.routers import DefaultRouter

from .views import ChecklistViewSet

router = DefaultRouter()
router.register(r"", ChecklistViewSet, basename="checklist")

urlpatterns = router.urls
