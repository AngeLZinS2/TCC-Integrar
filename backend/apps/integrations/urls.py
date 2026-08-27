from django.urls import path

from .views import (
    BancosSuportadosView,
    ConnectionView,
    DiscoveryView,
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
]
