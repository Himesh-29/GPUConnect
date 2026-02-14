"""Tests for computing utilities."""
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.test import TestCase

from ..models import Node
from ..utils import get_provider_stats

User = get_user_model()


class GetProviderStatsTests(TestCase):
    """Test provider stats utility function."""

    def setUp(self):
        """Set up test data."""
        self.provider = User.objects.create_user(
            username='provider', password='pass',
            wallet_balance=Decimal('100.00'),
        )
        self.consumer = User.objects.create_user(
            username='consumer', password='pass',
        )
        self.node = Node.objects.create(
            owner=self.provider,
            node_id='node-1',
            name='Node 1',
            gpu_info={'gpu_model': 'RTX 4090', 'count': 1},
            is_active=True,
        )

    def test_get_provider_stats_returns_dict(self):
        """get_provider_stats returns a dictionary."""
        stats = get_provider_stats(self.provider)
        self.assertIsInstance(stats, dict)

    def test_get_provider_stats_has_provider_data(self):
        """get_provider_stats includes provider data."""
        stats = get_provider_stats(self.provider)
        self.assertIn('active_nodes', stats['provider'])
        self.assertIn('total_earnings', stats['provider'])

    def test_get_provider_stats_has_consumer_data(self):
        """get_provider_stats includes consumer data."""
        stats = get_provider_stats(self.provider)
        self.assertIn('total_spent', stats['consumer'])
        self.assertIn('total_jobs', stats['consumer'])

    def test_get_provider_stats_has_wallet_balance(self):
        """get_provider_stats includes wallet balance."""
        stats = get_provider_stats(self.provider)
        self.assertIn('wallet_balance', stats)
        self.assertEqual(stats['wallet_balance'], 100.0)

    def test_get_provider_stats_with_custom_days(self):
        """get_provider_stats accepts custom days parameter."""
        stats = get_provider_stats(self.provider, days=7)
        self.assertEqual(stats['period_days'], 7)
