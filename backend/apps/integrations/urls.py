from django.urls import path

from .views import (
    BancosSuportadosView,
    CamposDisponiveisView,
    ConsultaLivreView,
    ConnectionView,
    DiscoveryView,
    MappingView,
    PreviewView,
    TestConnectionView,
)

urlpatterns = [
    path("databases/", BancosSuportadosView.as_view(), name="integration_databases"),
    path("connection/", ConnectionView.as_view(), name="integration_connection"),
    path(
        "connection/test/",
        TestConnectionView.as_view(),
        name="integration_connection_test",
    ),
    path("discovery/", DiscoveryView.as_view(), name="integration_discovery"),
    path("preview/", PreviewView.as_view(), name="integration_preview"),
    path("fields/", CamposDisponiveisView.as_view(), name="integration_fields"),
    path("query/", ConsultaLivreView.as_view(), name="integration_query"),
    path("mappings/", MappingView.as_view(), name="integration_mappings"),
    path(
        "mappings/<str:entidade>/",
        MappingView.as_view(),
        name="integration_mapping",
    ),
]
