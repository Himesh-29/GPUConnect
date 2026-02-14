"""Tests for core authentication adapters."""
from django.contrib.auth import get_user_model
from django.test import TestCase, RequestFactory

from core.adapters import MySocialAccountAdapter

User = get_user_model()


class SocialAccountAdapterTests(TestCase):
    """Test custom social account adapter."""

    def setUp(self):
        """Set up test data."""
        self.adapter = MySocialAccountAdapter()
        self.factory = RequestFactory()

    def test_adapter_instantiation(self):
        """MySocialAccountAdapter can be instantiated."""
        self.assertIsNotNone(self.adapter)

    def test_adapter_has_auto_signup(self):
        """Adapter has is_auto_signup_allowed method."""
        self.assertTrue(hasattr(self.adapter, 'is_auto_signup_allowed'))

    def test_adapter_has_populate_user(self):
        """Adapter has populate_user method."""
        self.assertTrue(hasattr(self.adapter, 'populate_user'))

    def test_adapter_allows_signup(self):
        """Adapter allows auto signup."""
        request = self.factory.get('/')
        result = self.adapter.is_auto_signup_allowed(request, None)
        self.assertTrue(result)

    def test_adapter_has_error_handler(self):
        """Adapter has on_authentication_error method."""
        self.assertTrue(hasattr(self.adapter, 'on_authentication_error'))
