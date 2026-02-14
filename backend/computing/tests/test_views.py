"""Tests for computing module views and utils."""
from django.contrib.auth import get_user_model
from django.test import TestCase
from rest_framework.test import APIClient
from rest_framework import status
from ..models import Node, Job
from ..utils import find_best_node

User = get_user_model()


class FindBestNodeTests(TestCase):
    """Test node matching algorithm."""

    def setUp(self):
        # Create provider user
        self.provider = User.objects.create_user(
            username='provider',
            password='pass',
            role='provider'
        )
        self.provider.wallet_balance = 1000
        self.provider.save()

        # Create nodes
        self.node1 = Node.objects.create(
            provider=self.provider,
            node_id='node-1',
            gpu_model='RTX 4090',
            gpu_count=2,
            price_per_unit=10.0,
            is_active=True
        )
        self.node2 = Node.objects.create(
            provider=self.provider,
            node_id='node-2',
            gpu_model='RTX 3090',
            gpu_count=1,
            price_per_unit=5.0,
            is_active=True
        )

    def test_finds_best_node(self):
        """find_best_node returns the most suitable node."""
        best = find_best_node()
        self.assertIsNotNone(best)
        self.assertIn(best.node_id, ['node-1', 'node-2'])

    def test_no_nodes_returns_none(self):
        """find_best_node returns None when no active nodes exist."""
        Node.objects.all().update(is_active=False)
        best = find_best_node()
        self.assertIsNone(best)

    def test_prefers_active_nodes(self):
        """find_best_node only returns active nodes."""
        self.node1.is_active = False
        self.node1.save()
        best = find_best_node()
        self.assertEqual(best.node_id, 'node-2')


class NodeListViewTests(TestCase):
    """Test node listing endpoint."""

    def setUp(self):
        self.client = APIClient()
        self.user = User.objects.create_user(
            username='consumer',
            password='pass'
        )
        self.provider = User.objects.create_user(
            username='provider',
            password='pass',
            role='provider'
        )
        self.node = Node.objects.create(
            provider=self.provider,
            node_id='test-node',
            gpu_model='RTX 4090',
            gpu_count=1,
            price_per_unit=10.0,
            is_active=True
        )

    def test_list_nodes_no_auth(self):
        """Node list accessible without auth."""
        response = self.client.get('/api/computing/nodes/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_list_only_active_nodes(self):
        """Node list only shows active nodes."""
        response = self.client.get('/api/computing/nodes/')
        self.assertEqual(len(response.data), 1)

        # Deactivate node
        self.node.is_active = False
        self.node.save()

        response = self.client.get('/api/computing/nodes/')
        self.assertEqual(len(response.data), 0)

    def test_node_includes_required_fields(self):
        """Node data includes all required fields."""
        response = self.client.get('/api/computing/nodes/')
        self.assertEqual(len(response.data), 1)
        node_data = response.data[0]
        self.assertIn('node_id', node_data)
        self.assertIn('gpu_model', node_data)
        self.assertIn('gpu_count', node_data)
        self.assertIn('price_per_unit', node_data)


class JobDetailViewTests(TestCase):
    """Test job detail endpoint."""

    def setUp(self):
        self.client = APIClient()
        self.user = User.objects.create_user(
            username='user1',
            password='pass'
        )
        self.user2 = User.objects.create_user(
            username='user2',
            password='pass'
        )
        self.provider = User.objects.create_user(
            username='provider',
            password='pass',
            role='provider'
        )
        self.node = Node.objects.create(
            provider=self.provider,
            node_id='test-node',
            gpu_model='RTX 4090',
            gpu_count=1,
            price_per_unit=10.0,
            is_active=True
        )
        self.job = Job.objects.create(
            user=self.user,
            node=self.node,
            prompt='test prompt',
            model='llama2'
        )

    def test_job_detail_requires_auth(self):
        """Job detail requires authentication."""
        response = self.client.get(f'/api/computing/jobs/{self.job.id}/')
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_owner_can_view_job(self):
        """Job owner can view job details."""
        self.client.force_authenticate(user=self.user)
        response = self.client.get(f'/api/computing/jobs/{self.job.id}/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['id'], self.job.id)

    def test_other_users_cannot_view_job(self):
        """Other users cannot view someone else's job."""
        self.client.force_authenticate(user=self.user2)
        response = self.client.get(f'/api/computing/jobs/{self.job.id}/')
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_job_detail_nonexistent(self):
        """Requesting nonexistent job returns 404."""
        self.client.force_authenticate(user=self.user)
        response = self.client.get('/api/computing/jobs/99999/')
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
