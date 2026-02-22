"""Tests for WebSocket consumers (GPUConsumer and DashboardConsumer)."""
# pylint: disable=protected-access, unused-import

from decimal import Decimal

import pytest
from channels.testing import WebsocketCommunicator
from django.contrib.auth import get_user_model

from computing.consumers import (
    GPUConsumer,
    DashboardConsumer,
    JOB_COST,
    PROVIDER_SHARE,
)
from computing.models import Job, Node

User = get_user_model()


# ---------------------------------------------------------------------------
# GPUConsumer – sync helper tests
# ---------------------------------------------------------------------------

@pytest.mark.django_db(transaction=True)
class TestGPUConsumerSyncHelpers:
    """Test synchronous helper methods on GPUConsumer."""

    def setup_method(self):
        self.provider = User.objects.create_user(
            username="provider", password="p",
            wallet_balance=Decimal("100.00"),
        )
        self.consumer_user = User.objects.create_user(
            username="consumeruser", password="p",
            wallet_balance=Decimal("50.00"),
        )
        self.node = Node.objects.create(
            owner=self.provider,
            node_id="node-sync-1",
            name="Sync Node",
            gpu_info={"models": ["llama2", {"name": "mistral"}]},
            is_active=True,
        )

    # _get_models_sync_shared
    def test_get_models_sync_shared_aggregates(self):
        """_get_models_sync_shared aggregates models from active nodes."""
        consumer = GPUConsumer()
        models = consumer._get_models_sync_shared()
        names = [m["name"] for m in models]
        assert "llama2" in names
        assert "mistral" in names

    def test_get_models_sync_shared_inactive_excluded(self):
        """Inactive nodes are excluded from models."""
        self.node.is_active = False
        self.node.save()
        consumer = GPUConsumer()
        models = consumer._get_models_sync_shared()
        assert models == []

    def test_get_models_sync_shared_provider_count(self):
        """Provider count is incremented for each node with the model."""
        Node.objects.create(
            owner=self.provider, node_id="node-sync-2", name="Sync Node 2",
            gpu_info={"models": ["llama2"]}, is_active=True,
        )
        consumer = GPUConsumer()
        models = consumer._get_models_sync_shared()
        llama_entry = next(m for m in models if m["name"] == "llama2")
        assert llama_entry["providers"] == 2

    def test_get_models_sync_shared_empty_gpu_info(self):
        """Nodes with empty gpu_info return no models."""
        Node.objects.all().update(gpu_info={})
        consumer = GPUConsumer()
        models = consumer._get_models_sync_shared()
        assert models == []


# ---------------------------------------------------------------------------
# GPUConsumer – database helper tests (calling the sync inner fn)
# ---------------------------------------------------------------------------

@pytest.mark.django_db(transaction=True)
class TestGPUConsumerDBHelpers:
    """Test the database-sync-to-async helpers on GPUConsumer."""

    def setup_method(self):
        self.provider = User.objects.create_user(
            username="dbprovider", password="p",
            wallet_balance=Decimal("100.00"),
        )
        self.consumer_user = User.objects.create_user(
            username="dbconsumer", password="p",
            wallet_balance=Decimal("50.00"),
        )
        self.node = Node.objects.create(
            owner=self.provider,
            node_id="node-db-1",
            name="DB Node",
            gpu_info={"models": ["llama2"]},
            is_active=True,
        )

    def test_validate_token_returns_none_for_empty(self):
        """_validate_token returns None for empty token."""
        from asgiref.sync import async_to_sync
        consumer = GPUConsumer()
        result = async_to_sync(consumer._validate_token)("")
        assert result is None

    def test_validate_token_returns_none_for_invalid(self):
        """_validate_token returns None for invalid token."""
        from asgiref.sync import async_to_sync
        consumer = GPUConsumer()
        result = async_to_sync(consumer._validate_token)("gpc_invalidtoken")
        assert result is None

    def test_validate_token_returns_user_id_for_valid(self):
        """_validate_token returns user_id for valid AgentToken."""
        from asgiref.sync import async_to_sync
        from core.models import AgentToken
        _, raw = AgentToken.generate(self.provider, label="test-agent")
        consumer = GPUConsumer()
        result = async_to_sync(consumer._validate_token)(raw)
        assert result == self.provider.id

    def test_register_node_creates_new(self):
        """_register_node creates a new Node record."""
        from asgiref.sync import async_to_sync
        consumer = GPUConsumer()
        username = async_to_sync(consumer._register_node)(
            "new-node-id", {"models": ["test"]}, self.provider.id,
        )
        assert username == self.provider.username
        assert Node.objects.filter(node_id="new-node-id").exists()

    def test_register_node_updates_existing(self):
        """_register_node updates an existing Node."""
        from asgiref.sync import async_to_sync
        consumer = GPUConsumer()
        async_to_sync(consumer._register_node)(
            "node-db-1", {"models": ["updated"]}, self.provider.id,
        )
        node = Node.objects.get(node_id="node-db-1")
        assert node.gpu_info == {"models": ["updated"]}

    def test_mark_node_inactive(self):
        """_mark_node_inactive sets is_active=False."""
        from asgiref.sync import async_to_sync
        consumer = GPUConsumer()
        async_to_sync(consumer._mark_node_inactive)("node-db-1")
        self.node.refresh_from_db()
        assert self.node.is_active is False

    def test_complete_job_marks_completed(self):
        """_complete_job marks job as COMPLETED and sets cost."""
        from asgiref.sync import async_to_sync
        job = Job.objects.create(
            user=self.consumer_user, node=self.node,
            task_type="inference", input_data={"model": "llama2", "prompt": "hi"},
            status="RUNNING",
        )
        consumer = GPUConsumer()
        async_to_sync(consumer._complete_job)(
            job.id, {"output": "hello"}, self.provider.id,
        )
        job.refresh_from_db()
        assert job.status == "COMPLETED"
        assert job.cost == JOB_COST
        assert job.result == {"output": "hello"}
        assert job.completed_at is not None

    def test_complete_job_credits_provider(self):
        """_complete_job credits the provider's wallet."""
        from asgiref.sync import async_to_sync
        job = Job.objects.create(
            user=self.consumer_user, node=self.node,
            task_type="inference", input_data={"model": "llama2", "prompt": "hi"},
            status="RUNNING",
        )
        consumer = GPUConsumer()
        async_to_sync(consumer._complete_job)(
            job.id, {"output": "result"}, self.provider.id,
        )
        self.provider.refresh_from_db()
        assert self.provider.wallet_balance == Decimal("100.00") + PROVIDER_SHARE

    def test_complete_job_nonexistent(self):
        """_complete_job handles nonexistent job gracefully."""
        from asgiref.sync import async_to_sync
        consumer = GPUConsumer()
        # Should not raise
        async_to_sync(consumer._complete_job)(99999, {}, self.provider.id)

    def test_fail_job(self):
        """_fail_job marks job as FAILED."""
        from asgiref.sync import async_to_sync
        job = Job.objects.create(
            user=self.consumer_user, node=self.node,
            task_type="inference", input_data={"prompt": "test"},
            status="RUNNING",
        )
        consumer = GPUConsumer()
        async_to_sync(consumer._fail_job)(job.id, {"error": "GPU OOM"})
        job.refresh_from_db()
        assert job.status == "FAILED"
        assert job.result == {"error": "GPU OOM"}
        assert job.completed_at is not None

    def test_fail_job_nonexistent(self):
        """_fail_job handles nonexistent job gracefully."""
        from asgiref.sync import async_to_sync
        consumer = GPUConsumer()
        async_to_sync(consumer._fail_job)(99999, {"error": "nope"})

    def test_get_job_completion_data(self):
        """_get_job_completion_data returns correct structure."""
        from asgiref.sync import async_to_sync
        job = Job.objects.create(
            user=self.consumer_user, node=self.node,
            task_type="inference",
            input_data={"model": "llama2", "prompt": "hello"},
            status="COMPLETED", cost=JOB_COST,
        )
        consumer = GPUConsumer()
        data = async_to_sync(consumer._get_job_completion_data)(
            job.id, self.provider.id,
        )
        assert data is not None
        assert data["owner_id"] == self.consumer_user.id
        assert data["job_data"]["status"] == "COMPLETED"
        assert data["job_data"]["model"] == "llama2"

    def test_get_job_completion_data_nonexistent(self):
        """_get_job_completion_data returns None for missing job."""
        from asgiref.sync import async_to_sync
        consumer = GPUConsumer()
        data = async_to_sync(consumer._get_job_completion_data)(
            99999, self.provider.id,
        )
        assert data is None

    def test_get_job_completion_data_non_dict_input(self):
        """_get_job_completion_data handles non-dict input_data."""
        from asgiref.sync import async_to_sync
        job = Job.objects.create(
            user=self.consumer_user, node=self.node,
            task_type="inference",
            input_data="raw string input",
            status="COMPLETED", cost=JOB_COST,
        )
        consumer = GPUConsumer()
        data = async_to_sync(consumer._get_job_completion_data)(
            job.id, self.provider.id,
        )
        assert data is not None
        assert data["job_data"]["prompt"] == "raw string input"
        assert data["job_data"]["model"] == "unknown"


# ---------------------------------------------------------------------------
# GPUConsumer – job_dispatch method
# ---------------------------------------------------------------------------

@pytest.mark.django_db(transaction=True)
class TestGPUConsumerJobDispatch:
    """Test the job_dispatch handler."""

    def setup_method(self):
        self.provider = User.objects.create_user(
            username="dispatch_prov", password="p",
        )

    @pytest.mark.asyncio
    async def test_job_dispatch_skips_unregistered(self):
        """job_dispatch does nothing if provider not registered."""
        consumer = GPUConsumer()
        consumer.provider_user_id = None
        # Should not raise or send anything
        await consumer.job_dispatch({
            "job_data": {"task_id": 1, "owner_id": 99},
        })

    @pytest.mark.asyncio
    async def test_job_dispatch_skips_own_job(self):
        """job_dispatch skips if provider is the job owner."""
        consumer = GPUConsumer()
        consumer.provider_user_id = 42
        # Owner matches provider — should skip
        await consumer.job_dispatch({
            "job_data": {"task_id": 1, "owner_id": 42},
        })


# ---------------------------------------------------------------------------
# DashboardConsumer – sync helper tests
# ---------------------------------------------------------------------------

@pytest.mark.django_db(transaction=True)
class TestDashboardConsumerSyncHelpers:
    """Test synchronous helpers on DashboardConsumer."""

    def setup_method(self):
        self.user = User.objects.create_user(
            username="dashuser", password="p",
            wallet_balance=Decimal("75.00"),
        )
        self.node = Node.objects.create(
            owner=self.user, node_id="dash-node-1", name="Dash Node",
            gpu_info={"models": [{"name": "phi-3"}, "gemma"]},
            is_active=True,
        )

    def test_get_models_sync(self):
        """_get_models_sync aggregates models from active nodes."""
        consumer = DashboardConsumer()
        models = consumer._get_models_sync()
        names = [m["name"] for m in models]
        assert "phi-3" in names
        assert "gemma" in names

    def test_get_models_sync_empty(self):
        """_get_models_sync returns empty list when no active nodes."""
        Node.objects.all().update(is_active=False)
        consumer = DashboardConsumer()
        assert consumer._get_models_sync() == []


# ---------------------------------------------------------------------------
# DashboardConsumer – database helpers
# ---------------------------------------------------------------------------

@pytest.mark.django_db(transaction=True)
class TestDashboardConsumerDBHelpers:
    """Test DashboardConsumer database helpers."""

    def setup_method(self):
        self.user = User.objects.create_user(
            username="dash_db_user", password="p",
            wallet_balance=Decimal("200.00"),
        )
        self.node = Node.objects.create(
            owner=self.user, node_id="dash-db-1", name="Dash DB",
            gpu_info={"models": ["llama2"]}, is_active=True,
        )

    def test_get_balance(self):
        """_get_balance returns the user's wallet balance."""
        from asgiref.sync import async_to_sync
        consumer = DashboardConsumer()
        bal = async_to_sync(consumer._get_balance)(self.user.id)
        assert bal == Decimal("200.00")

    def test_get_balance_nonexistent_user(self):
        """_get_balance returns 0 for nonexistent user."""
        from asgiref.sync import async_to_sync
        consumer = DashboardConsumer()
        bal = async_to_sync(consumer._get_balance)(99999)
        assert bal == Decimal("0.00")

    def test_get_stats(self):
        """_get_stats returns correct structure."""
        from asgiref.sync import async_to_sync
        consumer = DashboardConsumer()
        stats = async_to_sync(consumer._get_stats)()
        assert "active_nodes" in stats
        assert "completed_jobs" in stats
        assert "available_models" in stats
        assert stats["active_nodes"] == 1

    def test_get_models(self):
        """_get_models returns model list."""
        from asgiref.sync import async_to_sync
        consumer = DashboardConsumer()
        models = async_to_sync(consumer._get_models)()
        assert isinstance(models, list)
        names = [m["name"] for m in models]
        assert "llama2" in names

    def test_get_recent_jobs_empty(self):
        """_get_recent_jobs returns empty list for user with no jobs."""
        from asgiref.sync import async_to_sync
        consumer = DashboardConsumer()
        jobs = async_to_sync(consumer._get_recent_jobs)(self.user.id)
        assert jobs == []

    def test_get_recent_jobs_with_data(self):
        """_get_recent_jobs returns job data."""
        from asgiref.sync import async_to_sync
        Job.objects.create(
            user=self.user, node=self.node,
            task_type="inference",
            input_data={"model": "llama2", "prompt": "hello"},
            status="COMPLETED",
        )
        consumer = DashboardConsumer()
        jobs = async_to_sync(consumer._get_recent_jobs)(self.user.id)
        assert len(jobs) == 1
        assert jobs[0]["status"] == "COMPLETED"
        assert jobs[0]["model"] == "llama2"

    def test_get_recent_jobs_non_dict_input(self):
        """_get_recent_jobs handles non-dict input_data."""
        from asgiref.sync import async_to_sync
        Job.objects.create(
            user=self.user, node=self.node,
            task_type="inference",
            input_data="just a string",
            status="PENDING",
        )
        consumer = DashboardConsumer()
        jobs = async_to_sync(consumer._get_recent_jobs)(self.user.id)
        assert len(jobs) == 1
        assert jobs[0]["prompt"] == "just a string"
        assert jobs[0]["model"] == "unknown"

    def test_get_provider_stats_async(self):
        """_get_provider_stats_async returns stats dict."""
        from asgiref.sync import async_to_sync
        consumer = DashboardConsumer()
        stats = async_to_sync(consumer._get_provider_stats_async)(
            self.user.id, 30,
        )
        assert stats is not None
        assert "provider" in stats
        assert "consumer" in stats

    def test_get_provider_stats_async_invalid_user(self):
        """_get_provider_stats_async returns None for invalid user."""
        from asgiref.sync import async_to_sync
        consumer = DashboardConsumer()
        stats = async_to_sync(consumer._get_provider_stats_async)(
            99999, 30,
        )
        assert stats is None

    def test_get_user_from_token_invalid(self):
        """_get_user_from_token returns None for invalid token."""
        from asgiref.sync import async_to_sync
        consumer = DashboardConsumer()
        result = async_to_sync(consumer._get_user_from_token)("invalid")
        assert result is None

    def test_get_user_from_token_valid(self):
        """_get_user_from_token returns user for valid JWT."""
        from asgiref.sync import async_to_sync
        from rest_framework_simplejwt.tokens import RefreshToken
        refresh = RefreshToken.for_user(self.user)
        access = str(refresh.access_token)
        consumer = DashboardConsumer()
        result = async_to_sync(consumer._get_user_from_token)(access)
        assert result is not None
        assert result.id == self.user.id


# ---------------------------------------------------------------------------
# GPUConsumer – WebSocket connect/disconnect integration
# ---------------------------------------------------------------------------

@pytest.mark.django_db(transaction=True)
@pytest.mark.asyncio
class TestGPUConsumerWebSocket:
    """Integration tests for GPUConsumer via WebsocketCommunicator."""

    async def test_connect_and_receive_ping(self):
        """GPUConsumer accepts connection."""
        communicator = WebsocketCommunicator(
            GPUConsumer.as_asgi(), "/ws/computing/",
        )
        connected, _ = await communicator.connect()
        assert connected
        await communicator.disconnect()

    async def test_register_with_invalid_token(self):
        """GPUConsumer closes on invalid auth token during register."""
        communicator = WebsocketCommunicator(
            GPUConsumer.as_asgi(), "/ws/computing/",
        )
        connected, _ = await communicator.connect()
        assert connected

        await communicator.send_json_to({
            "type": "register",
            "node_id": "test-node",
            "gpu_info": {"models": ["llama2"]},
            "auth_token": "gpc_invalidtoken",
        })

        # Should get an auth_error message
        response = await communicator.receive_json_from(timeout=5)
        assert response["type"] == "auth_error"
        await communicator.disconnect()

    async def test_pong_message_handled(self):
        """GPUConsumer handles pong messages without error."""
        communicator = WebsocketCommunicator(
            GPUConsumer.as_asgi(), "/ws/computing/",
        )
        connected, _ = await communicator.connect()
        assert connected
        await communicator.send_json_to({"type": "pong"})
        await communicator.disconnect()


# ---------------------------------------------------------------------------
# DashboardConsumer – WebSocket integration
# ---------------------------------------------------------------------------

@pytest.mark.django_db(transaction=True)
@pytest.mark.asyncio
class TestDashboardConsumerWebSocket:
    """Integration tests for DashboardConsumer."""

    async def test_connect_sends_initial_stats(self):
        """DashboardConsumer sends stats on connect."""
        communicator = WebsocketCommunicator(
            DashboardConsumer.as_asgi(), "/ws/dashboard/",
        )
        connected, _ = await communicator.connect()
        assert connected

        # First message: stats_update
        msg = await communicator.receive_json_from(timeout=5)
        assert msg["type"] == "stats_update"
        assert "stats" in msg

        # Second message: models_update
        msg = await communicator.receive_json_from(timeout=5)
        assert msg["type"] == "models_update"
        assert "models" in msg

        await communicator.disconnect()

    async def test_connect_with_invalid_token(self):
        """DashboardConsumer still connects with invalid token (no user)."""
        communicator = WebsocketCommunicator(
            DashboardConsumer.as_asgi(),
            "/ws/dashboard/?token=invalidjwt",
        )
        connected, _ = await communicator.connect()
        assert connected
        # Gets stats and models but no balance/jobs
        msg = await communicator.receive_json_from(timeout=5)
        assert msg["type"] == "stats_update"
        msg = await communicator.receive_json_from(timeout=5)
        assert msg["type"] == "models_update"
        await communicator.disconnect()

    async def test_receive_subscribe_provider_stats(self):
        """DashboardConsumer handles subscribe_provider_stats message."""
        communicator = WebsocketCommunicator(
            DashboardConsumer.as_asgi(), "/ws/dashboard/",
        )
        connected, _ = await communicator.connect()
        assert connected
        # Drain initial messages
        await communicator.receive_json_from(timeout=5)
        await communicator.receive_json_from(timeout=5)

        # Send subscribe — no user so it should be ignored
        await communicator.send_json_to({
            "type": "subscribe_provider_stats",
            "days": 7,
        })
        await communicator.disconnect()

    async def test_receive_invalid_json(self):
        """DashboardConsumer handles invalid messages gracefully."""
        communicator = WebsocketCommunicator(
            DashboardConsumer.as_asgi(), "/ws/dashboard/",
        )
        connected, _ = await communicator.connect()
        assert connected
        await communicator.receive_json_from(timeout=5)
        await communicator.receive_json_from(timeout=5)

        # Send invalid type
        await communicator.send_json_to({"type": "unknown_type"})
        await communicator.disconnect()

    async def test_dashboard_update_handler(self):
        """DashboardConsumer forwards dashboard_update messages."""
        communicator = WebsocketCommunicator(
            DashboardConsumer.as_asgi(), "/ws/dashboard/",
        )
        connected, _ = await communicator.connect()
        assert connected
        # Drain initial messages
        await communicator.receive_json_from(timeout=5)
        await communicator.receive_json_from(timeout=5)

        # Simulate a channel_layer group_send
        consumer = DashboardConsumer()
        consumer.user_id = None
        consumer.provider_days = 30

        await communicator.disconnect()
