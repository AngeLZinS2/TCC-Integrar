from django.urls import path
from rest_framework.routers import DefaultRouter

from .views import (
    DocumentAcceptView,
    DocumentCategoryViewSet,
    DocumentDownloadView,
    DocumentViewSet,
    MyPendingDocumentsView,
)

router = DefaultRouter()
router.register(r"categories", DocumentCategoryViewSet, basename="documentcategory")
router.register(r"", DocumentViewSet, basename="document")

# As rotas literais vêm antes das do router: o detalhe é /<pk>/ com regex
# genérica e capturaria "pending" como se fosse um id.
urlpatterns = [
    path("pending/", MyPendingDocumentsView.as_view(), name="documents_pending"),
    path(
        "<int:pk>/versions/<int:version_id>/download/",
        DocumentDownloadView.as_view(),
        name="document_download",
    ),
    path(
        "<int:pk>/versions/<int:version_id>/accept/",
        DocumentAcceptView.as_view(),
        name="document_accept",
    ),
] + router.urls
