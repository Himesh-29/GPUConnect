"""
Test Suite: Authentication & User Registration
Covers: POST /api/core/register/, POST /api/core/token/, GET /api/core/profile/
"""
import pytest
from rest_framework.test import APIClient
from django.urls import reverse
from core.models import User
from decimal import Decimal


@pytest.mark.django_db
class TestRegistration:
    """Tests for POST /api/core/register/"""

    def setup_method(self):
        self.client = APIClient()

    def test_register_success(self):
        resp = self.client.post(reverse('register'), {
            'username': 'newuser',
            'email': 'new@test.com',
            'password': 'strongpassword',
            'role': 'USER'
        }, format='json')
        assert resp.status_code == 201
        assert User.objects.filter(username='newuser').exists()

    def test_register_creates_user_with_default_balance(self):
        self.client.post(reverse('register'), {
            'username': 'rich',
            'email': 'rich@test.com',
            'password': 'strongpassword',
        }, format='json')
        user = User.objects.get(username='rich')
        assert user.wallet_balance == Decimal('100.00')

    def test_register_with_provider_role(self):
        self.client.post(reverse('register'), {
            'username': 'gpugod',
            'email': 'gpu@test.com',
            'password': 'strongpassword',
            'role': 'PROVIDER'
        }, format='json')
        user = User.objects.get(username='gpugod')
        assert user.role == 'PROVIDER'

    def test_register_duplicate_username_fails(self):
        User.objects.create_user(username='taken', password='pass')
        resp = self.client.post(reverse('register'), {
            'username': 'taken',
            'email': 'dupe@test.com',
            'password': 'strongpassword',
        }, format='json')
        assert resp.status_code == 400

    def test_register_missing_password_fails(self):
        resp = self.client.post(reverse('register'), {
            'username': 'nopass',
            'email': 'nopass@test.com',
        }, format='json')
        assert resp.status_code == 400

    def test_register_missing_username_fails(self):
        resp = self.client.post(reverse('register'), {
            'email': 'noname@test.com',
            'password': 'strongpassword',
        }, format='json')
        assert resp.status_code == 400


@pytest.mark.django_db
class TestLogin:
    """Tests for POST /api/core/token/"""

    def setup_method(self):
        self.client = APIClient()
        self.user = User.objects.create_user(username='alice', password='secure123')

    def test_login_success(self):
        resp = self.client.post(reverse('token_obtain_pair'), {
            'username': 'alice',
            'password': 'secure123'
        }, format='json')
        assert resp.status_code == 200
        assert 'access' in resp.data
        assert 'refresh' in resp.data

    def test_login_wrong_password(self):
        resp = self.client.post(reverse('token_obtain_pair'), {
            'username': 'alice',
            'password': 'wrongpass'
        }, format='json')
        assert resp.status_code == 401

    def test_login_nonexistent_user(self):
        resp = self.client.post(reverse('token_obtain_pair'), {
            'username': 'ghost',
            'password': 'whatever'
        }, format='json')
        assert resp.status_code == 401


@pytest.mark.django_db
class TestProfile:
    """Tests for GET /api/core/profile/"""

    def setup_method(self):
        self.client = APIClient()
        self.user = User.objects.create_user(
            username='profileuser', password='pass123',
            email='profile@test.com', role='PROVIDER',
            wallet_balance=Decimal('42.50')
        )

    def test_get_profile_authenticated(self):
        self.client.force_authenticate(user=self.user)
        resp = self.client.get(reverse('profile'))
        assert resp.status_code == 200
        assert resp.data['username'] == 'profileuser'
        assert resp.data['email'] == 'profile@test.com'
        assert resp.data['role'] == 'PROVIDER'

    def test_get_profile_unauthenticated(self):
        resp = self.client.get(reverse('profile'))
        assert resp.status_code == 401

    def test_profile_includes_wallet_balance(self):
        self.client.force_authenticate(user=self.user)
        resp = self.client.get(reverse('profile'))
        assert 'wallet_balance' in resp.data
