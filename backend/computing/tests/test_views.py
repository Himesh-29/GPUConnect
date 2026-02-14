"""Tests for computing module views."""
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.test import TestCase
from rest_framework import status
from rest_framework.test import APIClient

from ..models import Node, Job

User = get_user_model()


class AvailableModelsViewTests(TestCase):
    """Tests for GET /api/computing/models/"""

    def setUp(self):
        """Set up test data."""
        self.client = APIClient()
        self.provider = User.objects.create_user(
            username='provider', password='pass'
        )
        self.node = Node.objects.create(
            owner=self.provider,
            node_id='test-node-1',
            name='Test GPU Node',
            gpu_info={'models': ['llama3.2:latest', 'gemma3:270m']},
            is_active=True,
        )

    def test_models_endpoint_returns_200(self):
        """Available models endpoint returns 200 without auth."""
        response = self.client.get('/api/computing/models/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_models_lists_available_models(self):
        """Response includes models from active nodes."""
        response = self.client.get('/api/computing/models/')
        self.assertIn('models', response.data)
        self.assertGreater(len(response.data['models']), 0)

    def test_models_includes_total_nodes(self):
        """Response includes total active node count."""
        response = self.client.get('/api/computing/models/')
        self.assertIn('total_nodes', response.data)
        self.assertEqual(response.data['total_nodes'], 1)

    def test_inactive_node_models_excluded(self):
        """Inactive nodes don't contribute models."""
        self.node.is_active = False
        self.node.save()
        response = self.client.get('/api/computing/models/')
        self.assertEqual(len(response.data['models']), 0)
        self.assertEqual(response.data['total_nodes'], 0)


class NetworkStatsViewTests(TestCase):
    """Tests for GET /api/computing/stats/"""

    def setUp(self):
        """Set up test data."""
        self.client = APIClient()
        self.user = User.objects.create_user(
            username='consumer', password='pass'
        )
        self.provider = User.objects.create_user(
            username='provider', password='pass'
        )
        self.node = Node.objects.create(
            owner=self.provider,
            node_id='stats-node',
            name='Stats Node',
            gpu_info={'models': ['llama3.2:latest']},
            is_active=True,
        )

    def test_stats_endpoint_returns_200(self):
        """Network stats returns 200 without auth."""
        response = self.client.get('/api/computing/stats/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_stats_includes_active_nodes(self):
        """Stats include active_nodes count."""
        response = self.client.get('/api/computing/stats/')
        self.assertEqual(response.data['active_nodes'], 1)

    def test_stats_includes_job_counts(self):
        """Stats include total_jobs and completed_jobs."""
        Job.objects.create(
            user=self.user, task_type='inference',
            input_data={'prompt': 'test'}, status='COMPLETED',
        )
        response = self.client.get('/api/computing/stats/')
        self.assertEqual(response.data['total_jobs'], 1)
        self.assertEqual(response.data['completed_jobs'], 1)

    def test_stats_includes_available_models(self):
        """Stats include available_models count."""
        response = self.client.get('/api/computing/stats/')
        self.assertIn('available_models', response.data)


class JobListViewTests(TestCase):
    """Tests for GET /api/computing/jobs/"""

    def setUp(self):
        """Set up test data."""
        self.client = APIClient()
        self.user = User.objects.create_user(
            username='consumer', password='pass'
        )
        self.provider = User.objects.create_user(
            username='provider', password='pass'
        )
        self.node = Node.objects.create(
            owner=self.provider,
            node_id='test-node-2',
            name='Test GPU Node 2',
            gpu_info={'count': 1},
            is_active=True,
        )
        self.job = Job.objects.create(
            user=self.user, node=self.node,
            task_type='inference',
            input_data={'prompt': 'test prompt', 'model': 'llama2'},
        )

    def test_job_list_requires_auth(self):
        """Job list requires authentication."""
        response = self.client.get('/api/computing/jobs/')
        self.assertEqual(
            response.status_code, status.HTTP_401_UNAUTHORIZED,
        )

    def test_user_can_list_own_jobs(self):
        """Authenticated user can list their jobs."""
        self.client.force_authenticate(user=self.user)
        response = self.client.get('/api/computing/jobs/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIsInstance(response.data, list)
        self.assertEqual(len(response.data), 1)

    def test_users_only_see_own_jobs(self):
        """Users only see their own jobs in the list."""
        user2 = User.objects.create_user(
            username='user2', password='pass',
        )
        Job.objects.create(
            user=user2, task_type='inference',
            input_data={'prompt': 'other', 'model': 'llama2'},
        )
        self.client.force_authenticate(user=self.user)
        response = self.client.get('/api/computing/jobs/')
        self.assertEqual(len(response.data), 1)


class ProviderStatsViewTests(TestCase):
    """Tests for GET /api/computing/provider-stats/"""

    def setUp(self):
        """Set up test data."""
        self.client = APIClient()
        self.user = User.objects.create_user(
            username='provider', password='pass',
            wallet_balance=Decimal('100.00'),
        )

    def test_provider_stats_requires_auth(self):
        """Provider stats requires authentication."""
        response = self.client.get('/api/computing/provider-stats/')
        self.assertEqual(
            response.status_code, status.HTTP_401_UNAUTHORIZED,
        )

    def test_provider_stats_returns_200(self):
        """Authenticated user gets provider stats."""
        self.client.force_authenticate(user=self.user)
        response = self.client.get('/api/computing/provider-stats/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_provider_stats_has_expected_keys(self):
        """Provider stats response includes provider/consumer/wallet keys."""
        self.client.force_authenticate(user=self.user)
        response = self.client.get('/api/computing/provider-stats/')
        self.assertIn('provider', response.data)
        self.assertIn('consumer', response.data)
        self.assertIn('wallet_balance', response.data)

    def test_provider_stats_custom_days(self):
        """Provider stats accepts days query parameter."""
        self.client.force_authenticate(user=self.user)
        response = self.client.get(
            '/api/computing/provider-stats/?days=7',
        )
        self.assertEqual(response.data['period_days'], 7)
