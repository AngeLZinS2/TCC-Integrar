from rest_framework.routers import DefaultRouter

from .views import PositionViewSet, SectorViewSet

router = DefaultRouter()
router.register(r"positions", PositionViewSet, basename="position")
router.register(r"", SectorViewSet, basename="sector")

urlpatterns = router.urls
