"""Tests for core views (auth, profile, health check, agent tokens)."""
import json
from django.contrib.auth import get_user_model
from django.test import TestCase
from rest_framework.test import APIClient
from rest_framework import status
from ..models import AgentToken

User = get_user_model()


class HealthCheckViewTests(TestCase):
    """Test health check endpoint."""

    def setUp(self):
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
        self.client.force_authenticate(user=None)
        response = self.client.get('/api/core/health/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)


class UserProfileViewTests(TestCase):
    """Test user profile retrieval and update."""

    def setUp(self):
        self.client = APIClient()
        self.user = User.objects.create_user(
            username='testuser',
            password='testpass123',
            email='test@example.com'
        )

    def test_profile_requires_auth(self):
        """Profile endpoint requires authentication."""
        response = self.client.get('/api/core/profile/')
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_get_own_profile(self):
        """Authenticated user can retrieve their profile."""
        self.client.force_authenticate(user=self.user)
        response = self.client.get('/api/core/profile/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['username'], 'testuser')
        self.assertEqual(response.data['email'], 'test@example.com')

    def test_update_profile_email(self):
        """User can update their email."""
        self.client.force_authenticate(user=self.user)
        response = self.client.patch('/api/core/profile/', {'email': 'newemail@example.com'})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.user.refresh_from_db()
        self.assertEqual(self.user.email, 'newemail@example.com')

    def test_cannot_change_username(self):
        """Username should not be changeable."""
        self.client.force_authenticate(user=self.user)
        response = self.client.patch('/api/core/profile/', {'username': 'newusername'})
        self.user.refresh_from_db()
        self.assertEqual(self.user.username, 'testuser')


class AgentTokenGenerateViewTests(TestCase):
    """Test agent token generation."""

    def setUp(self):
        self.client = APIClient()
        self.user = User.objects.create_user(
            username='testuser',
            password='testpass123'
        )
        self.client.force_authenticate(user=self.user)

    def test_generate_token_success(self):
        """User can generate an agent token."""
        response = self.client.post('/api/core/agent-tokens/generate/', {'label': 'My Agent'})
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertIn('token', response.data)
        self.assertIn('id', response.data)
        self.assertEqual(response.data['label'], 'My Agent')

    def test_generate_token_without_label_uses_default(self):
        """Generating token without label uses 'Default Agent'."""
        response = self.client.post('/api/core/agent-tokens/generate/')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data['label'], 'Default Agent')

    def test_max_5_active_tokens(self):
        """User cannot have more than 5 active tokens."""
        # Generate 5 tokens
        for i in range(5):
            response = self.client.post('/api/core/agent-tokens/generate/', {'label': f'Token {i}'})
            self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        # Try to generate 6th token - should fail
        response = self.client.post('/api/core/agent-tokens/generate/', {'label': 'Token 6'})
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('error', response.data)

    def test_revoke_token_frees_slot(self):
        """Revoking a token allows generating a new one."""
        # Generate 5 tokens
        token_ids = []
        for i in range(5):
            response = self.client.post('/api/core/agent-tokens/generate/', {'label': f'Token {i}'})
            token_ids.append(response.data['id'])

        # Revoke first token
        self.client.delete(f'/api/core/agent-tokens/{token_ids[0]}/')

        # Now should be able to generate a 6th token
        response = self.client.post('/api/core/agent-tokens/generate/', {'label': 'Token 6'})
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

    def test_generate_token_requires_auth(self):
        """Generating token requires authentication."""
        self.client.force_authenticate(user=None)
        response = self.client.post('/api/core/agent-tokens/generate/', {'label': 'Test'})
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)


class AgentTokenListViewTests(TestCase):
    """Test agent token list endpoint."""

    def setUp(self):
        self.client = APIClient()
        self.user = User.objects.create_user(
            username='testuser',
            password='testpass123'
        )
        self.client.force_authenticate(user=self.user)

    def test_list_tokens(self):
        """User can list their agent tokens."""
        # Create 3 tokens
        for i in range(3):
            self.client.post('/api/core/agent-tokens/generate/', {'label': f'Token {i}'})

        response = self.client.get('/api/core/agent-tokens/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 3)

    def test_list_only_shows_user_tokens(self):
        """User only sees their own tokens."""
        # Create token for first user
        self.client.post('/api/core/agent-tokens/generate/', {'label': 'User1 Token'})

        # Create second user with token
        user2 = User.objects.create_user(username='testuser2', password='testpass123')
        self.client.force_authenticate(user=user2)
        self.client.post('/api/core/agent-tokens/generate/', {'label': 'User2 Token'})

        # Check first user only sees 1 token
        self.client.force_authenticate(user=self.user)
        response = self.client.get('/api/core/agent-tokens/')
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]['label'], 'User1 Token')

    def test_list_tokens_requires_auth(self):
        """Listing tokens requires authentication."""
        self.client.force_authenticate(user=None)
        response = self.client.get('/api/core/agent-tokens/')
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
