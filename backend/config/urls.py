"""
Root URL configuration.

Prefixo de versão: /api/v1/
Documentação:
  - /api/schema/   → OpenAPI JSON/YAML
  - /api/docs/     → Swagger UI
"""

from django.contrib import admin
from django.urls import include, path
from drf_spectacular.views import SpectacularAPIView, SpectacularSwaggerView

from apps.common.health import HealthCheckView

urlpatterns = [
    # Django admin (painel RH)
    path("admin/", admin.site.urls),

    # OpenAPI schema + Swagger UI
    path("api/schema/", SpectacularAPIView.as_view(), name="schema"),
    path("api/docs/", SpectacularSwaggerView.as_view(url_name="schema"), name="swagger-ui"),

    # API v1
    path(
        "api/v1/",
        include(
            [
                # Público: consultado pelo Docker antes de haver sessão.
                path("health/", HealthCheckView.as_view(), name="health"),
                path("auth/", include("apps.users.urls")),
                path("employees/", include("apps.users.employee_urls")),
                path("companies/", include("apps.companies.urls")),
                path("sectors/", include("apps.sectors.urls")),
                path("courses/", include("apps.courses.urls")),
                path("checklist/", include("apps.checklist.urls")),
                path("materials/", include("apps.materials.urls")),
                path("notifications/", include("apps.notifications.urls")),
                path("dashboard/", include("apps.dashboard.urls")),
                path("audit/", include("apps.audit.urls")),
                path("requests/", include("apps.requests.urls")),
                path("communications/", include("apps.communications.urls")),
                path("events/", include("apps.events.urls")),
                path("documents/", include("apps.documents.urls")),
                path("onboarding/", include("apps.onboarding.urls")),
                path("units/", include("apps.units.urls")),
                path("automations/", include("apps.automations.urls")),
                path("integrations/", include("apps.integrations.urls")),
            ]
        ),
    ),
]
