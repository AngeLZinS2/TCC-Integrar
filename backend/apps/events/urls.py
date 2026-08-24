from django.urls import path
from rest_framework.routers import DefaultRouter

from .views import EventViewSet, UpcomingBirthdaysView

router = DefaultRouter()
router.register(r"", EventViewSet, basename="event")

# A rota literal vem antes das do router: o detalhe é /<pk>/ com regex
# genérica e capturaria "birthdays" como se fosse um id.
urlpatterns = [
    path("birthdays/", UpcomingBirthdaysView.as_view(), name="upcoming_birthdays"),
] + router.urls
