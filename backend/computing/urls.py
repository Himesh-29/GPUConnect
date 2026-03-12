"""URL configuration for the computing module."""
from django.urls import path
from .views import (
    JobSubmissionView, JobDetailView, JobListView,
    AvailableModelsView, NetworkStatsView, ProviderStatsView,
    SessionListView, SessionDetailView
)

urlpatterns = [
    path('submit-job/', JobSubmissionView.as_view(), name='submit-job'),
    path('jobs/', JobListView.as_view(), name='job-list'),
    path('jobs/<int:job_id>/', JobDetailView.as_view(), name='job-detail'),
    path('models/', AvailableModelsView.as_view(), name='available-models'),
    path('stats/', NetworkStatsView.as_view(), name='network-stats'),
    path('provider-stats/', ProviderStatsView.as_view(), name='provider-stats'),
    path('sessions/', SessionListView.as_view(), name='session-list'),
    path('sessions/<str:session_id>/', SessionDetailView.as_view(), name='session-detail'),
]
