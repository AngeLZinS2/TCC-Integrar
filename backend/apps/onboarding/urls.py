from django.urls import path
from rest_framework.routers import DefaultRouter

from .views import (
    EmployeeOnboardingView,
    MyOnboardingView,
    OnboardingTaskViewSet,
    OnboardingTemplateViewSet,
)

router = DefaultRouter()
router.register(r"tasks", OnboardingTaskViewSet, basename="onboarding-task")
router.register(r"templates", OnboardingTemplateViewSet, basename="onboarding-template")

# Rotas literais antes do router: "my/" não pode ser capturado como um id.
urlpatterns = [
    path("my/", MyOnboardingView.as_view(), name="onboarding-my"),
    path(
        "employees/<int:employee_id>/",
        EmployeeOnboardingView.as_view(),
        name="onboarding-employee",
    ),
] + router.urls
