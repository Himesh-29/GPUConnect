"""
OAuth Views

Two views handle the OAuth flow:

1. OAuthCompleteView (LOGIN_REDIRECT_URL = /api/auth/oauth/complete/)
   - Called by django-allauth after OAuth dance completes
   - The browser is still on the backend domain, so the session cookie works
   - Generates JWT tokens and redirects to the frontend with tokens in URL hash
   - This avoids all cross-site cookie issues

2. OAuthCallbackView (legacy fallback)
   - Kept for backward compatibility
   - Called by frontend if it tries the old session-exchange flow

Flow:
  1. User clicks "Sign in with Google" on React frontend
  2. React redirects to /accounts/google/login/
  3. allauth handles OAuth dance → user logs in to Django session
  4. allauth redirects to LOGIN_REDIRECT_URL → /api/auth/oauth/complete/
  5. OAuthCompleteView generates JWT tokens
  6. Redirects to frontend: /oauth/callback#access=xxx&refresh=xxx&user=xxx
  7. React reads tokens from URL hash, stores them, done!
"""
from django.conf import settings
from django.http import JsonResponse, HttpResponseRedirect
from django.utils.http import urlencode
from rest_framework.views import APIView
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework.authentication import SessionAuthentication
import json
import urllib.parse


class OAuthCompleteView(APIView):
    """
    Called by allauth after OAuth completes (LOGIN_REDIRECT_URL).
    
    Since this is a same-domain redirect (browser is on onrender.com),
    the Django session cookie is available — no cross-site issues.
    
    Generates JWT tokens and redirects to the frontend with them in the
    URL fragment (hash), so they never appear in server logs.
    """
    authentication_classes = [SessionAuthentication]
    permission_classes = []

    def get(self, request):
        import logging
        logger = logging.getLogger(__name__)

        user = request.user
        frontend_url = getattr(settings, 'FRONTEND_URL', 'http://localhost:5173')

        if not user or not user.is_authenticated:
            logger.warning("OAuth complete called but user not authenticated")
            return HttpResponseRedirect(f"{frontend_url}/login?error=oauth_failed")

        # Generate JWT tokens
        refresh = RefreshToken.for_user(user)
        access_token = str(refresh.access_token)
        refresh_token = str(refresh)

        user_data = json.dumps({
            "id": user.id,
            "username": user.username,
            "email": user.email,
        })

        # Redirect to frontend with tokens in URL fragment (hash)
        # Fragment is never sent to the server, so tokens stay client-side
        fragment = urlencode({
            "access": access_token,
            "refresh": refresh_token,
            "user": user_data,
        })

        redirect_url = f"{frontend_url}/oauth/callback#{fragment}"
        logger.info(f"OAuth complete for user {user.username}, redirecting to frontend")

        return HttpResponseRedirect(redirect_url)


class OAuthCallbackView(APIView):
    """
    Legacy fallback: Exchange Django session for JWT via API call.
    Kept for backward compatibility but may fail in browsers that block
    cross-site cookies (Chrome, Firefox, Safari).
    """
    authentication_classes = [SessionAuthentication]
    permission_classes = []

    def get(self, request):
        user = request.user
        if not user or not user.is_authenticated:
            return JsonResponse(
                {"error": "Not authenticated. Please complete OAuth login first."},
                status=401
            )

        refresh = RefreshToken.for_user(user)

        return JsonResponse({
            "access": str(refresh.access_token),
            "refresh": str(refresh),
            "user": {
                "id": user.id,
                "username": user.username,
                "email": user.email,
            }
        })
