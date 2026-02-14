"""Tests for computing serializers."""
from django.contrib.auth import get_user_model
from django.test import TestCase

from ..models import Node, Job
from ..serializers import NodeSerializer, JobSerializer

User = get_user_model()


class NodeSerializerTests(TestCase):
    """Test Node serializer."""

    def setUp(self):
        """Set up test data."""
        self.user = User.objects.create_user(
            username='provider', password='pass'
        )
        self.node = Node.objects.create(
            owner=self.user,
            node_id='test-node',
            name='Test Node',
            gpu_info={'gpu_model': 'RTX 4090', 'count': 1},
            is_active=True,
        )

    def test_serialize_node(self):
        """NodeSerializer can serialize a Node instance."""
        serializer = NodeSerializer(self.node)
        data = serializer.data
        self.assertEqual(data['node_id'], 'test-node')
        self.assertEqual(data['name'], 'Test Node')

    def test_node_serializer_includes_required_fields(self):
        """NodeSerializer includes required fields."""
        serializer = NodeSerializer(self.node)
        data = serializer.data
        self.assertIn('node_id', data)
        self.assertIn('name', data)
        self.assertIn('is_active', data)

    def test_node_serializer_gpu_info(self):
        """NodeSerializer includes GPU info."""
        serializer = NodeSerializer(self.node)
        data = serializer.data
        self.assertIn('gpu_info', data)
        self.assertEqual(data['gpu_info']['gpu_model'], 'RTX 4090')


class JobSerializerTests(TestCase):
    """Test Job serializer."""

    def setUp(self):
        """Set up test data."""
        self.user = User.objects.create_user(
            username='user', password='pass'
        )
        self.provider = User.objects.create_user(
            username='provider', password='pass'
        )
        self.node = Node.objects.create(
            owner=self.provider,
            node_id='test-node',
            name='Test Node',
            gpu_info={'count': 1},
            is_active=True,
        )
        self.job = Job.objects.create(
            user=self.user,
            node=self.node,
            task_type='inference',
            input_data={'prompt': 'test', 'model': 'llama2'},
        )

    def test_serialize_job(self):
        """JobSerializer can serialize a Job instance."""
        serializer = JobSerializer(self.job)
        data = serializer.data
        self.assertEqual(data['task_type'], 'inference')
        self.assertEqual(data['status'], 'PENDING')

    def test_job_serializer_includes_required_fields(self):
        """JobSerializer includes required fields."""
        serializer = JobSerializer(self.job)
        data = serializer.data
        self.assertIn('task_type', data)
        self.assertIn('status', data)
        self.assertIn('input_data', data)

    def test_job_serializer_user_id(self):
        """JobSerializer includes user ID."""
        serializer = JobSerializer(self.job)
        data = serializer.data
        self.assertEqual(data['user'], self.user.id)

    def test_create_job_via_serializer(self):
        """JobSerializer can create a new Job."""
        data = {
            'task_type': 'training',
            'input_data': {'epochs': 10},
        }
        serializer = JobSerializer(data=data)
        self.assertTrue(serializer.is_valid(), serializer.errors)
        job = serializer.save(user=self.user, node=self.node)
        self.assertEqual(job.task_type, 'training')
        self.assertEqual(job.user, self.user)
        self.assertEqual(job.node, self.node)
