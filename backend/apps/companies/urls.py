from django.urls import path
from rest_framework.routers import DefaultRouter

from .my_company import CompanySetupChecklistView, MyCompanyView
from .views import CompanyViewSet

router = DefaultRouter()
router.register(r"", CompanyViewSet, basename="company")

# As rotas /me/ vêm ANTES das do router: o router registra o detalhe como
# /<pk>/ com regex genérica, que capturaria "me" como se fosse um id.
urlpatterns = [
    path("me/", MyCompanyView.as_view(), name="my_company"),
    path("me/setup/", CompanySetupChecklistView.as_view(), name="my_company_setup"),
] + router.urls
