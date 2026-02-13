"""
Test Suite: Core User Model
Covers: User creation, password hashing, wallet defaults
"""
import pytest
from core.models import User
from decimal import Decimal


@pytest.mark.django_db
def test_user_creation():
    user = User.objects.create_user(username='testuser', password='password')
    assert user.username == 'testuser'
    assert user.check_password('password')
    assert user.wallet_balance == Decimal('100.00')  # PoC default


@pytest.mark.django_db
def test_wallet_update():
    user = User.objects.create_user(username='testuser', password='password')
    user.wallet_balance += Decimal('50.00')
    user.save()
    user.refresh_from_db()
    assert user.wallet_balance == Decimal('150.00')


@pytest.mark.django_db
def test_wallet_deduction():
    user = User.objects.create_user(username='spender', password='password')
    user.wallet_balance -= Decimal('25.00')
    user.save()
    user.refresh_from_db()
    assert user.wallet_balance == Decimal('75.00')
