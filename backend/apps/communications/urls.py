from django.urls import path

from . import views

urlpatterns = [
    path('', views.AnnouncementListCreateView.as_view(), name='announcement-list'),
    path('<int:pk>/', views.AnnouncementDetailView.as_view(), name='announcement-detail'),
    path('<int:pk>/read/', views.MarkAsReadView.as_view(), name='announcement-read'),
    path('<int:pk>/publish/', views.AnnouncementPublishView.as_view(), name='announcement-publish'),
]
