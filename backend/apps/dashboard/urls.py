from django.urls import path

from .p2_views import HRDashboardView, MyHomeView, TeamDashboardView
from .views import (
    CollaboratorDetailView,
    CollaboratorListView,
    CollaboratorsExportView,
    DashboardOverviewView,
)

urlpatterns = [
    path("overview/", DashboardOverviewView.as_view(), name="dashboard_overview"),
    path("hr/", HRDashboardView.as_view(), name="dashboard_hr"),
    path("me/", MyHomeView.as_view(), name="dashboard_me"),
    path("team/", TeamDashboardView.as_view(), name="dashboard_team"),
    path("collaborators/", CollaboratorListView.as_view(), name="dashboard_collaborators"),
    path("collaborators/export/", CollaboratorsExportView.as_view(), name="dashboard_collaborators_export"),
    path("collaborators/<int:pk>/", CollaboratorDetailView.as_view(), name="dashboard_collaborator_detail"),
]
