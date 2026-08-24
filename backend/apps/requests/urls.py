from django.urls import path
from rest_framework.routers import DefaultRouter

from .views import HRRequestViewSet, RequestAttachmentDownloadView

router = DefaultRouter()
router.register(r"", HRRequestViewSet, basename="hrrequest")

urlpatterns = [
    path(
        "<int:pk>/attachments/<int:attachment_id>/download/",
        RequestAttachmentDownloadView.as_view(),
        name="request_attachment_download",
    ),
] + router.urls
