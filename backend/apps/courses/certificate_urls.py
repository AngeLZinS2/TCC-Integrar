from django.urls import path
from rest_framework.routers import DefaultRouter

from .quiz_views import CertificateValidationView, CertificateViewSet

router = DefaultRouter()
router.register(r"", CertificateViewSet, basename="certificate")

# A rota pública de validação vem antes das do router — o detalhe usa
# `code` como lookup e capturaria "validate" como se fosse um código.
urlpatterns = [
    path(
        "validate/<str:code>/",
        CertificateValidationView.as_view(),
        name="certificate_validate",
    ),
] + router.urls
