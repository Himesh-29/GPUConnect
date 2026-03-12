"""
Test Suite: Job Submission Flow
Covers: JobSubmissionView - credit deduction, validation, persistence
"""
from decimal import Decimal

import pytest
from django.urls import reverse
from rest_framework.test import APIClient

from computing.models import Job, Node
from core.models import User


@pytest.mark.django_db
class TestJobSubmissionAPI:
    """Tests for POST /api/computing/submit-job/"""

    def setup_method(self):
        self.client = APIClient()
        self.consumer = User.objects.create_user(
            username='consumer', password='StrongPass123!',
            wallet_balance=Decimal('10.00')
        )
        self.provider = User.objects.create_user(
            username='provider', password='StrongPass456!', role='PROVIDER',
            wallet_balance=Decimal('0.00')
        )
        self.node = Node.objects.create(
            node_id="node-1", owner=self.provider,
            name="Test GPU", gpu_info={"model": "RTX 4090"}, is_active=True
        )
        # Authenticate as consumer
        self.client.force_authenticate(user=self.consumer)

    # --- Happy Path ---
    def test_submit_job_success(self):
        """POST with a valid prompt returns 201."""
        resp = self.client.post(
            reverse('submit-job'),
            {"prompt": "Hello world"}, format='json',
        )
        assert resp.status_code == 201
        assert resp.data['status'] == 'submitted'
        assert 'job_id' in resp.data

    def test_job_created_in_db(self):
        """Submitted job is persisted with correct fields."""
        self.client.post(
            reverse('submit-job'),
            {"prompt": "Test", "model": "gemma3:270m"}, format='json',
        )
        job = Job.objects.first()
        assert job is not None
        assert job.user == self.consumer
        assert job.task_type == 'inference'
        assert job.input_data['prompt'] == 'Test'
        assert job.input_data['model'] == 'gemma3:270m'
        assert job.status == 'PENDING'

    def test_cost_saved_on_job(self):  # pylint: disable=missing-function-docstring
        self.client.post(reverse('submit-job'), {"prompt": "X"}, format='json')
        job = Job.objects.first()
        assert job.cost == Decimal('1.00')

    def test_credit_deducted_on_submit(self):  # pylint: disable=missing-function-docstring
        self.client.post(reverse('submit-job'), {"prompt": "X"}, format='json')
        self.consumer.refresh_from_db()
        assert self.consumer.wallet_balance == Decimal('9.00')

    def test_multiple_jobs_deduct_correctly(self):  # pylint: disable=missing-function-docstring
        for i in range(3):
            self.client.post(reverse('submit-job'), {"prompt": f"Job {i}"}, format='json')
        self.consumer.refresh_from_db()
        assert self.consumer.wallet_balance == Decimal('7.00')
        assert Job.objects.filter(user=self.consumer).count() == 3

    def test_default_model_is_llama(self):  # pylint: disable=missing-function-docstring
        self.client.post(reverse('submit-job'), {"prompt": "Hello"}, format='json')
        job = Job.objects.first()
        assert job.input_data['model'] == 'llama3.2:latest'

    # --- Validation ---
    def test_missing_prompt_returns_400(self):  # pylint: disable=missing-function-docstring
        resp = self.client.post(reverse('submit-job'), {"model": "llama3.2:latest"}, format='json')
        assert resp.status_code == 400

    def test_empty_prompt_returns_400(self):  # pylint: disable=missing-function-docstring
        resp = self.client.post(reverse('submit-job'), {"prompt": ""}, format='json')
        assert resp.status_code == 400

    def test_no_job_created_on_validation_error(self):  # pylint: disable=missing-function-docstring
        self.client.post(reverse('submit-job'), {}, format='json')
        assert Job.objects.count() == 0

    # --- Insufficient Funds ---
    def test_insufficient_funds_returns_402(self):  # pylint: disable=missing-function-docstring
        self.consumer.wallet_balance = Decimal('0.50')
        self.consumer.save()
        resp = self.client.post(reverse('submit-job'), {"prompt": "Test"}, format='json')
        assert resp.status_code == 402

    def test_zero_balance_returns_402(self):  # pylint: disable=missing-function-docstring
        self.consumer.wallet_balance = Decimal('0.00')
        self.consumer.save()
        resp = self.client.post(reverse('submit-job'), {"prompt": "Test"}, format='json')
        assert resp.status_code == 402

    def test_no_deduction_on_insufficient_funds(self):  # pylint: disable=missing-function-docstring
        self.consumer.wallet_balance = Decimal('0.50')
        self.consumer.save()
        self.client.post(reverse('submit-job'), {"prompt": "Test"}, format='json')
        self.consumer.refresh_from_db()
        assert self.consumer.wallet_balance == Decimal('0.50')

    # --- Auth ---
    def test_unauthenticated_returns_401(self):  # pylint: disable=missing-function-docstring
        client = APIClient()  # No auth
        resp = client.post(reverse('submit-job'), {"prompt": "Hello"}, format='json')
        assert resp.status_code == 401

    # --- Job List ---
    def test_job_list_returns_user_jobs(self):  # pylint: disable=missing-function-docstring
        self.client.post(reverse('submit-job'), {"prompt": "A"}, format='json')
        self.client.post(reverse('submit-job'), {"prompt": "B"}, format='json')
        resp = self.client.get(reverse('job-list'))
        assert resp.status_code == 200
        assert len(resp.data) == 2

    def test_job_list_excludes_other_users(self):  # pylint: disable=missing-function-docstring
        self.client.post(reverse('submit-job'), {"prompt": "Mine"}, format='json')
        # Switch to another user
        other = User.objects.create_user(
            username='other', password='OtherPass1!',
            wallet_balance=Decimal('10.00'),
        )
        self.client.force_authenticate(user=other)
        self.client.post(reverse('submit-job'), {"prompt": "Theirs"}, format='json')
        # Check other user sees only their job
        resp = self.client.get(reverse('job-list'))
        assert len(resp.data) == 1
        assert resp.data[0]['prompt'] == 'Theirs'


@pytest.mark.django_db
class TestStreamingPricing:
    """Tests for streaming surcharge on POST /api/computing/submit-job/"""

    def setup_method(self):
        self.client = APIClient()
        self.consumer = User.objects.create_user(
            username='stream_consumer', password='StrongPass123!',
            wallet_balance=Decimal('10.00')
        )
        self.provider = User.objects.create_user(
            username='stream_provider', password='StrongPass456!', role='PROVIDER',
        )
        self.node = Node.objects.create(
            node_id="stream-node-1", owner=self.provider,
            name="Stream GPU", gpu_info={"model": "RTX 4090"}, is_active=True
        )
        self.client.force_authenticate(user=self.consumer)

    def test_non_stream_job_costs_one_dollar(self):
        """Non-streaming jobs deduct exactly $1.00."""
        self.client.post(
            reverse('submit-job'),
            {"prompt": "Hello", "stream": False}, format='json',
        )
        self.consumer.refresh_from_db()
        assert self.consumer.wallet_balance == Decimal('9.00')
        assert Job.objects.first().cost == Decimal('1.00')

    def test_stream_job_costs_one_dollar_five(self):
        """Streaming jobs deduct $1.05 (base + surcharge)."""
        self.client.post(
            reverse('submit-job'),
            {"prompt": "Hello", "stream": True}, format='json',
        )
        self.consumer.refresh_from_db()
        assert self.consumer.wallet_balance == Decimal('8.95')
        assert Job.objects.first().cost == Decimal('1.05')

    def test_stream_string_true_treated_as_streaming(self):
        """stream='true' (string) is coerced to True and applies streaming surcharge."""
        self.client.post(
            reverse('submit-job'),
            {"prompt": "Hello", "stream": "true"}, format='json',
        )
        self.consumer.refresh_from_db()
        assert self.consumer.wallet_balance == Decimal('8.95')

    def test_stream_string_false_treated_as_non_streaming(self):
        """stream='false' (string) is coerced to False and uses base cost."""
        self.client.post(
            reverse('submit-job'),
            {"prompt": "Hello", "stream": "false"}, format='json',
        )
        self.consumer.refresh_from_db()
        assert self.consumer.wallet_balance == Decimal('9.00')

    def test_insufficient_funds_for_streaming_no_deduction(self):
        """Wallet is not charged when balance is below streaming cost."""
        self.consumer.wallet_balance = Decimal('1.04')
        self.consumer.save()
        resp = self.client.post(
            reverse('submit-job'),
            {"prompt": "Hello", "stream": True}, format='json',
        )
        assert resp.status_code == 402
        self.consumer.refresh_from_db()
        assert self.consumer.wallet_balance == Decimal('1.04')

    def test_invalid_session_no_deduction(self):
        """Wallet is not charged when session_id does not exist."""
        resp = self.client.post(
            reverse('submit-job'),
            {"prompt": "Hello", "session_id": 999999},
            format='json',
        )
        assert resp.status_code == 404
        self.consumer.refresh_from_db()
        assert self.consumer.wallet_balance == Decimal('10.00')


@pytest.mark.django_db
class TestSessionAPI:
    """Tests for /api/computing/sessions/ REST endpoints."""

    def setup_method(self):
        self.client = APIClient()
        self.user = User.objects.create_user(
            username='session_user', password='Pass123!',
        )
        self.other = User.objects.create_user(
            username='other_user', password='Pass456!',
        )
        self.client.force_authenticate(user=self.user)

    # --- List ---
    def test_list_sessions_requires_auth(self):
        """Session list requires authentication."""
        resp = APIClient().get(reverse('session-list'))
        assert resp.status_code == 401

    def test_list_returns_only_own_sessions(self):
        """GET /sessions/ returns only the requester's sessions."""
        from computing.models import ChatSession
        ChatSession.objects.create(user=self.user, name='Mine')
        ChatSession.objects.create(user=self.other, name='Theirs')
        resp = self.client.get(reverse('session-list'))
        assert resp.status_code == 200
        assert len(resp.data) == 1
        assert resp.data[0]['name'] == 'Mine'

    def test_list_returns_string_ids(self):
        """Session list serializes id as a string."""
        from computing.models import ChatSession
        ChatSession.objects.create(user=self.user, name='Test')
        resp = self.client.get(reverse('session-list'))
        assert isinstance(resp.data[0]['id'], str)

    # --- Create ---
    def test_create_session(self):
        """POST /sessions/ creates a session with given name."""
        resp = self.client.post(reverse('session-list'), {'name': 'My Session'}, format='json')
        assert resp.status_code == 201
        assert resp.data['name'] == 'My Session'
        assert isinstance(resp.data['id'], str)

    def test_create_session_name_too_long_returns_400(self):
        """POST with a name exceeding 255 chars returns 400."""
        resp = self.client.post(
            reverse('session-list'), {'name': 'x' * 256}, format='json',
        )
        assert resp.status_code == 400

    def test_create_session_default_name(self):
        """POST without a name creates session with default 'New Chat' name."""
        resp = self.client.post(reverse('session-list'), {}, format='json')
        assert resp.status_code == 201
        assert resp.data['name'] == 'New Chat'

    # --- Rename ---
    def test_rename_session(self):
        """PATCH /sessions/<id>/ updates the session name."""
        from computing.models import ChatSession
        session = ChatSession.objects.create(user=self.user, name='Old Name')
        resp = self.client.patch(
            reverse('session-detail', kwargs={'session_id': str(session.id)}),
            {'name': 'New Name'}, format='json',
        )
        assert resp.status_code == 200
        session.refresh_from_db()
        assert session.name == 'New Name'

    def test_rename_other_users_session_returns_404(self):
        """PATCH on another user's session returns 404 (not 403)."""
        from computing.models import ChatSession
        other_session = ChatSession.objects.create(user=self.other, name='Theirs')
        resp = self.client.patch(
            reverse('session-detail', kwargs={'session_id': str(other_session.id)}),
            {'name': 'Hacked'}, format='json',
        )
        assert resp.status_code == 404

    def test_rename_with_empty_name_returns_400(self):
        """PATCH with no name returns 400."""
        from computing.models import ChatSession
        session = ChatSession.objects.create(user=self.user, name='Mine')
        resp = self.client.patch(
            reverse('session-detail', kwargs={'session_id': str(session.id)}),
            {}, format='json',
        )
        assert resp.status_code == 400

    # --- Delete ---
    def test_delete_session(self):
        """DELETE /sessions/<id>/ removes the session."""
        from computing.models import ChatSession
        session = ChatSession.objects.create(user=self.user, name='To Delete')
        resp = self.client.delete(
            reverse('session-detail', kwargs={'session_id': str(session.id)}),
        )
        assert resp.status_code == 204
        assert not ChatSession.objects.filter(id=session.id).exists()

    def test_delete_other_users_session_returns_404(self):
        """DELETE on another user's session returns 404."""
        from computing.models import ChatSession
        other_session = ChatSession.objects.create(user=self.other, name='Theirs')
        resp = self.client.delete(
            reverse('session-detail', kwargs={'session_id': str(other_session.id)}),
        )
        assert resp.status_code == 404
        assert ChatSession.objects.filter(id=other_session.id).exists()
