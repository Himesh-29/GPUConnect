from django.urls import path
from .oauth_views import OAuthCallbackView, OAuthCompleteView

urlpatterns = [
    path('', OAuthCallbackView.as_view(), name='oauth-callback'),
    path('complete/', OAuthCompleteView.as_view(), name='oauth-complete'),
]
