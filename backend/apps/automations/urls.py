from django.urls import path
from rest_framework.routers import DefaultRouter

from .views import AutomationCatalogView, AutomationRuleViewSet

router = DefaultRouter()
router.register(r"rules", AutomationRuleViewSet, basename="automation-rule")

urlpatterns = [
    path("catalog/", AutomationCatalogView.as_view(), name="automation-catalog"),
] + router.urls
