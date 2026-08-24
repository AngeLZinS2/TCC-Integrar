from rest_framework.routers import DefaultRouter

from django.urls import path

from .views import NotificationPreferenceView, NotificationViewSet

router = DefaultRouter()
router.register(r"", NotificationViewSet, basename="notification")

# A rota literal vem antes das do router: o detalhe e /<pk>/ com regex
# generica e capturaria "preferences" como se fosse um id.
urlpatterns = [
    path("preferences/", NotificationPreferenceView.as_view(), name="notification_preferences"),
] + router.urls
