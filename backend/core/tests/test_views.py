"""Tests for core views (auth, profile, health check, agent tokens)."""
from django.contrib.auth import get_user_model
from django.test import TestCase
from rest_framework import status
from rest_framework.test import APIClient

User = get_user_model()


class HealthCheckViewTests(TestCase):
    """Test health check endpoint."""

    def setUp(self):
        """Set up test client."""
        self.client = APIClient()

    def test_health_check_returns_200(self):
        """Health check endpoint returns 200."""
        response = self.client.get('/api/core/health/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_health_check_returns_status(self):
        """Health check returns status field."""
        response = self.client.get('/api/core/health/')
        self.assertIn('status', response.data)
        self.assertEqual(response.data['status'], 'healthy')

    def test_health_check_requires_no_auth(self):
        """Health check is accessible without authentication."""
        response = self.client.get('/api/core/health/')
        self.assertNotEqual(
            response.status_code, status.HTTP_401_UNAUTHORIZED,
        )


class UserProfileViewTests(TestCase):
    """Test user profile retrieval and update."""

    def setUp(self):
        """Set up test client and user."""
        self.client = APIClient()
        self.user = User.objects.create_user(
            username='testuser', password='testpass123',
            email='test@example.com',
        )

    def test_profile_requires_auth(self):
        """Profile endpoint requires authentication."""
        response = self.client.get('/api/core/profile/')
        self.assertEqual(
            response.status_code, status.HTTP_401_UNAUTHORIZED,
        )

    def test_get_own_profile(self):
        """Authenticated user can retrieve their profile."""
        self.client.force_authenticate(user=self.user)
        response = self.client.get('/api/core/profile/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['username'], 'testuser')

    def test_update_profile_email(self):
        """User can update their email."""
        self.client.force_authenticate(user=self.user)
        response = self.client.patch(
            '/api/core/profile/',
            {'email': 'newemail@example.com'},
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.user.refresh_from_db()
        self.assertEqual(self.user.email, 'newemail@example.com')


class AgentTokenGenerateViewTests(TestCase):
    """Test agent token generation."""

    def setUp(self):
        """Set up test client and authenticated user."""
        self.client = APIClient()
        self.user = User.objects.create_user(
            username='testuser', password='testpass123',
        )
        self.client.force_authenticate(user=self.user)

    def test_generate_token_success(self):
        """User can generate an agent token."""
        response = self.client.post(
            '/api/core/agent-token/generate/',
            {'label': 'My Agent'},
        )
        self.assertEqual(
            response.status_code, status.HTTP_201_CREATED,
        )
        self.assertIn('token', response.data)
        self.assertIn('id', response.data)
        self.assertEqual(response.data['label'], 'My Agent')

    def test_generate_token_without_label(self):
        """Generating token without label uses default."""
        response = self.client.post(
            '/api/core/agent-token/generate/',
        )
        self.assertEqual(
            response.status_code, status.HTTP_201_CREATED,
        )
        self.assertIn('token', response.data)

    def test_max_5_active_tokens(self):
        """User cannot have more than 5 active tokens."""
        for i in range(5):
            self.client.post(
                '/api/core/agent-token/generate/',
                {'label': f'Token {i}'},
            )
        response = self.client.post(
            '/api/core/agent-token/generate/',
            {'label': 'Token 6'},
        )
        self.assertEqual(
            response.status_code, status.HTTP_400_BAD_REQUEST,
        )
        self.assertIn('error', response.data)

    def test_generate_token_requires_auth(self):
        """Generating token requires authentication."""
        self.client.force_authenticate(user=None)
        response = self.client.post(
            '/api/core/agent-token/generate/',
            {'label': 'Test'},
        )
        self.assertEqual(
            response.status_code, status.HTTP_401_UNAUTHORIZED,
        )


class AgentTokenListViewTests(TestCase):
    """Test agent token list endpoint."""

    def setUp(self):
        """Set up test client and authenticated user."""
        self.client = APIClient()
        self.user = User.objects.create_user(
            username='testuser', password='testpass123',
        )
        self.client.force_authenticate(user=self.user)

    def test_list_tokens(self):
        """User can list their agent tokens."""
        for i in range(3):
            self.client.post(
                '/api/core/agent-token/generate/',
                {'label': f'Token {i}'},
            )
        response = self.client.get('/api/core/agent-token/list/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 3)

    def test_list_only_shows_user_tokens(self):
        """User only sees their own tokens."""
        self.client.post(
            '/api/core/agent-token/generate/',
            {'label': 'User1 Token'},
        )
        user2 = User.objects.create_user(
            username='testuser2', password='testpass123',
        )
        self.client.force_authenticate(user=user2)
        self.client.post(
            '/api/core/agent-token/generate/',
            {'label': 'User2 Token'},
        )
        self.client.force_authenticate(user=self.user)
        response = self.client.get('/api/core/agent-token/list/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)

    def test_list_tokens_requires_auth(self):
        """Listing tokens requires authentication."""
        self.client.force_authenticate(user=None)
        response = self.client.get('/api/core/agent-token/list/')
        self.assertEqual(
            response.status_code, status.HTTP_401_UNAUTHORIZED,
        )


class AgentTokenRevokeViewTests(TestCase):
    """Test agent token revocation."""

    def setUp(self):
        """Set up test client, user, and a token."""
        self.client = APIClient()
        self.user = User.objects.create_user(
            username='testuser', password='testpass123',
        )
        self.client.force_authenticate(user=self.user)
        resp = self.client.post(
            '/api/core/agent-token/generate/',
            {'label': 'Revocable'},
        )
        self.token_id = resp.data['id']

    def test_revoke_token_success(self):
        """User can revoke their own token."""
        response = self.client.post(
            f'/api/core/agent-token/{self.token_id}/revoke/',
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['status'], 'revoked')

    def test_revoke_nonexistent_token(self):
        """Revoking a nonexistent token returns 404."""
        response = self.client.post(
            '/api/core/agent-token/99999/revoke/',
        )
        self.assertEqual(
            response.status_code, status.HTTP_404_NOT_FOUND,
        )

    def test_revoked_token_not_in_list(self):
        """Revoked token no longer appears in the active list."""
        self.client.post(
            f'/api/core/agent-token/{self.token_id}/revoke/',
        )
        response = self.client.get('/api/core/agent-token/list/')
        self.assertEqual(len(response.data), 0)
