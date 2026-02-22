"""Tests for OAuth views (OAuthCompleteView, OAuthCallbackView)."""

from django.contrib.auth import get_user_model
from django.test import TestCase, RequestFactory, override_settings

from core.oauth_views import OAuthCompleteView, OAuthCallbackView

User = get_user_model()


@override_settings(FRONTEND_URL="http://testfrontend.local")
class OAuthCompleteViewTests(TestCase):
    """Tests for the OAuthCompleteView."""

    def setUp(self):
        self.factory = RequestFactory()
        self.user = User.objects.create_user(
            username="oauthuser", password="p", email="oauth@example.com",
        )

    def test_authenticated_user_redirects_with_tokens(self):
        """Authenticated user gets redirected with JWT tokens in fragment."""
        request = self.factory.get("/api/auth/oauth/complete/")
        request.user = self.user
        # SessionAuthentication requires CSRF for unsafe methods;
        # GET is safe, but we need to mark session as authenticated.
        request.session = {}
        response = OAuthCompleteView.as_view()(request)
        self.assertEqual(response.status_code, 302)
        self.assertIn("http://testfrontend.local/oauth/callback#", response.url)
        self.assertIn("access=", response.url)
        self.assertIn("refresh=", response.url)
        self.assertIn("user=", response.url)

    def test_unauthenticated_redirects_to_login_error(self):
        """Unauthenticated user gets redirected to login with error."""
        from django.contrib.auth.models import AnonymousUser
        request = self.factory.get("/api/auth/oauth/complete/")
        request.user = AnonymousUser()
        request.session = {}
        response = OAuthCompleteView.as_view()(request)
        self.assertEqual(response.status_code, 302)
        self.assertIn("error=oauth_failed", response.url)


@override_settings(FRONTEND_URL="http://testfrontend.local")
class OAuthCallbackViewTests(TestCase):
    """Tests for the legacy OAuthCallbackView."""

    def setUp(self):
        self.factory = RequestFactory()
        self.user = User.objects.create_user(
            username="legacyuser", password="p", email="legacy@example.com",
        )

    def test_authenticated_user_gets_tokens(self):
        """Authenticated user receives JWT tokens as JSON."""
        request = self.factory.get("/api/auth/oauth/callback/")
        request.user = self.user
        request.session = {}
        response = OAuthCallbackView.as_view()(request)
        self.assertEqual(response.status_code, 200)
        data = response.json() if hasattr(response, 'json') else {}
        # The response is a JsonResponse so we decode content
        import json
        data = json.loads(response.content)
        self.assertIn("access", data)
        self.assertIn("refresh", data)
        self.assertIn("user", data)
        self.assertEqual(data["user"]["username"], "legacyuser")
        self.assertEqual(data["user"]["email"], "legacy@example.com")

    def test_unauthenticated_returns_401(self):
        """Unauthenticated request returns 401."""
        from django.contrib.auth.models import AnonymousUser
        request = self.factory.get("/api/auth/oauth/callback/")
        request.user = AnonymousUser()
        request.session = {}
        response = OAuthCallbackView.as_view()(request)
        self.assertEqual(response.status_code, 401)
        import json
        data = json.loads(response.content)
        self.assertIn("error", data)
