"""
Test Suite: Payment System
Covers: Wallet balance, deposit, credit transfer, mock webhook
"""
import pytest
from rest_framework.test import APIClient
from django.urls import reverse
from core.models import User
from payments.models import Transaction, CreditLog
from payments.services import CreditService
from decimal import Decimal


@pytest.mark.django_db
class TestCreditService:
    """Tests for CreditService business logic."""

    def setup_method(self):
        self.sender = User.objects.create_user(
            username='sender', password='p',
            wallet_balance=Decimal('50.00')
        )
        self.receiver = User.objects.create_user(
            username='receiver', password='p',
            wallet_balance=Decimal('10.00')
        )

    def test_transfer_credits_success(self):
        CreditService.transfer_credits(self.sender, self.receiver, Decimal('20.00'), job_id=1)
        self.sender.refresh_from_db()
        self.receiver.refresh_from_db()
        assert self.sender.wallet_balance == Decimal('30.00')
        assert self.receiver.wallet_balance == Decimal('30.00')

    def test_transfer_creates_credit_logs(self):
        CreditService.transfer_credits(self.sender, self.receiver, Decimal('5.00'), job_id=42)
        logs = CreditLog.objects.all()
        assert logs.count() == 2
        sender_log = CreditLog.objects.filter(user=self.sender).first()
        receiver_log = CreditLog.objects.filter(user=self.receiver).first()
        assert sender_log.amount == Decimal('-5.00')
        assert receiver_log.amount == Decimal('5.00')
        assert 'Job 42' in sender_log.description

    def test_transfer_insufficient_funds_raises(self):
        with pytest.raises(ValueError, match="Insufficient funds"):
            CreditService.transfer_credits(self.sender, self.receiver, Decimal('999.00'))

    def test_transfer_insufficient_funds_no_change(self):
        try:
            CreditService.transfer_credits(self.sender, self.receiver, Decimal('999.00'))
        except ValueError:
            pass
        self.sender.refresh_from_db()
        self.receiver.refresh_from_db()
        assert self.sender.wallet_balance == Decimal('50.00')
        assert self.receiver.wallet_balance == Decimal('10.00')


@pytest.mark.django_db
class TestDepositWebhookFlow:
    """Tests for deposit transaction + mock webhook processing."""

    def setup_method(self):
        self.client = APIClient()
        self.user = User.objects.create_user(
            username='depositor', password='p',
            wallet_balance=Decimal('10.00')
        )

    def test_process_deposit_adds_to_wallet(self):
        txn = Transaction.objects.create(
            user=self.user, amount=Decimal('50.00'),
            type='DEPOSIT', status='PENDING'
        )
        result = CreditService.process_transaction(txn.id)
        assert result is True
        self.user.refresh_from_db()
        assert self.user.wallet_balance == Decimal('60.00')

    def test_process_deposit_changes_status(self):
        txn = Transaction.objects.create(
            user=self.user, amount=Decimal('25.00'),
            type='DEPOSIT', status='PENDING'
        )
        CreditService.process_transaction(txn.id)
        txn.refresh_from_db()
        assert txn.status == 'SUCCESS'

    def test_process_already_completed(self):
        txn = Transaction.objects.create(
            user=self.user, amount=Decimal('25.00'),
            type='DEPOSIT', status='SUCCESS'
        )
        result = CreditService.process_transaction(txn.id)
        assert result is False

    def test_withdrawal_insufficient_fails(self):
        txn = Transaction.objects.create(
            user=self.user, amount=Decimal('999.00'),
            type='WITHDRAWAL', status='PENDING'
        )
        result = CreditService.process_transaction(txn.id)
        assert result is False
        txn.refresh_from_db()
        assert txn.status == 'FAILED'

    def test_mock_webhook_endpoint(self):
        txn = Transaction.objects.create(
            user=self.user, amount=Decimal('10.00'),
            type='DEPOSIT', status='PENDING'
        )
        url = reverse('mock-webhook', kwargs={'transaction_id': txn.id})
        resp = self.client.post(url)
        assert resp.status_code == 200
        self.user.refresh_from_db()
        assert self.user.wallet_balance == Decimal('20.00')

    def test_mock_webhook_nonexistent_transaction(self):
        url = reverse('mock-webhook', kwargs={'transaction_id': 99999})
        resp = self.client.post(url)
        assert resp.status_code == 400
