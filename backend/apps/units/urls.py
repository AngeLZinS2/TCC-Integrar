from rest_framework.routers import DefaultRouter

from .views import UnitViewSet

router = DefaultRouter()
router.register(r"", UnitViewSet, basename="unit")

urlpatterns = router.urls
