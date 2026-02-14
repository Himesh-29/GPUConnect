from django.urls import path
from rest_framework_simplejwt.views import (
    TokenObtainPairView,
    TokenRefreshView,
)
from .views import (
    RegisterView, UserProfileView,
    AgentTokenGenerateView, AgentTokenListView, AgentTokenRevokeView,
    HealthCheckView,
)

urlpatterns = [
    path('register/', RegisterView.as_view(), name='register'),
    path('profile/', UserProfileView.as_view(), name='profile'),
    path('token/', TokenObtainPairView.as_view(), name='token_obtain_pair'),
    path('token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
    # Agent Token Management
    path('agent-token/generate/', AgentTokenGenerateView.as_view(), name='agent-token-generate'),
    path('agent-token/list/', AgentTokenListView.as_view(), name='agent-token-list'),
    path('agent-token/<int:token_id>/revoke/', AgentTokenRevokeView.as_view(), name='agent-token-revoke'),
    # Health check for cron jobs and monitoring
    path('health/', HealthCheckView.as_view(), name='health-check'),
]
