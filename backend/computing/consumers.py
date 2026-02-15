"""WebSocket consumers for GPU node communication and dashboard updates."""
import asyncio
import json
import logging
from decimal import Decimal

from channels.db import database_sync_to_async
from channels.generic.websocket import AsyncWebsocketConsumer
from django.utils import timezone

from datetime import timedelta

logger = logging.getLogger(__name__)

JOB_COST = Decimal("1.00")
PROVIDER_SHARE = Decimal("1.00")

# Nodes with no heartbeat for this long are auto-marked inactive
NODE_STALE_THRESHOLD = timedelta(seconds=45)


def _cleanup_stale_nodes():
    """Mark nodes inactive if their last heartbeat is older than threshold."""
    from .models import Node  # pylint: disable=import-outside-toplevel
    cutoff = timezone.now() - NODE_STALE_THRESHOLD
    stale = Node.objects.filter(is_active=True, last_heartbeat__lt=cutoff)
    count = stale.update(is_active=False)
    if count:
        logger.info("Marked %d stale node(s) inactive (no heartbeat since %s)", count, cutoff)


class GPUConsumer(AsyncWebsocketConsumer):
    """Handles GPU provider node WebSocket connections and job dispatching."""

    async def connect(self):
        """Accept the WebSocket and start keep-alive pings."""
        self.node_id = "unknown"
        self.provider_user_id = None
        self.auth_token = None
        self.group_name = "gpu_nodes"
        await self.channel_layer.group_add(
            self.group_name,
            self.channel_name
        )
        await self.accept()
        logger.info("WebSocket Connected")
        self._ping_task = asyncio.ensure_future(self._keep_alive())

    async def _broadcast_dashboard_update(self):
        """Trigger a recalculation and broadcast to dashboard consumers."""
        stats = await self._get_stats()
        models = await self._get_models()

        await self.channel_layer.group_send(
            "dashboard_updates",
            {
                "type": "dashboard_update",
                "data": {
                    "type": "stats_update",
                    "stats": stats
                }
            }
        )
        await self.channel_layer.group_send(
            "dashboard_updates",
            {
                "type": "dashboard_update",
                "data": {
                    "type": "models_update",
                    "models": models
                }
            }
        )

    # Re-use the logic from DashboardConsumer
    @database_sync_to_async
    def _get_stats(self):
        """Return network stats: active nodes, completed jobs, model count."""
        from .models import Node, Job  # pylint: disable=import-outside-toplevel
        _cleanup_stale_nodes()
        active_nodes = Node.objects.filter(is_active=True).count()
        completed_jobs = Job.objects.filter(status="COMPLETED").count()
        models = self._get_models_sync_shared()
        return {
            "active_nodes": active_nodes,
            "completed_jobs": completed_jobs,
            "available_models": len(models)
        }

    @database_sync_to_async
    def _get_models(self):
        """Return available models aggregated from active nodes."""
        _cleanup_stale_nodes()
        return self._get_models_sync_shared()

    def _get_models_sync_shared(self):
        """Synchronous helper: aggregate model counts from active nodes."""
        from .models import Node  # pylint: disable=import-outside-toplevel
        nodes = Node.objects.filter(is_active=True)
        model_counts = {}
        for node in nodes:
            info = node.gpu_info or {}
            node_models = info.get("models", [])
            for m in node_models:
                if isinstance(m, dict):
                    name = m.get("name")
                else:
                    name = m
                if name:
                    model_counts[name] = model_counts.get(name, 0) + 1
        return [{"name": k, "providers": v} for k, v in model_counts.items()]

    async def _keep_alive(self):
        """Send periodic pings and RE-VALIDATE token to handle revocation."""
        try:
            while True:
                await asyncio.sleep(15)

                # Re-validate token if we are registered
                if self.auth_token:
                    user_id = await self._validate_token(self.auth_token)
                    if not user_id:
                        logger.warning(
                            "Token revoked for node %s. Disconnecting.",
                            self.node_id,
                        )
                        await self.send(json.dumps({
                            "type": "auth_error",
                            "error": "Token revoked or expired."
                        }, ensure_ascii=False))
                        await self.close()
                        return

                # Update node's last_heartbeat to keep it active
                if self.node_id != "unknown":
                    await self._touch_node_heartbeat(self.node_id)

                await self.send(json.dumps(
                    {"type": "ping"}, ensure_ascii=False,
                ))
        except Exception:  # pylint: disable=broad-except
            pass

    async def disconnect(self, close_code):
        """Clean up on WebSocket disconnect."""
        logger.info("WebSocket Disconnected: %s", close_code)
        if hasattr(self, '_ping_task'):
            self._ping_task.cancel()
        await self.channel_layer.group_discard(
            self.group_name,
            self.channel_name
        )
        if self.node_id != "unknown":
            await self._mark_node_inactive(self.node_id)
            await self._broadcast_dashboard_update()
            if self.provider_user_id:
                await self.channel_layer.group_send(
                    f"user_{self.provider_user_id}",
                    {
                        "type": "dashboard_update",
                        "data": {"type": "refresh_provider_stats"}
                    }
                )

    async def receive(self, text_data):
        """Route incoming WebSocket messages by type."""
        data = json.loads(text_data)
        msg_type = data.get("type")

        if msg_type == "register":
            self.node_id = data.get("node_id")
            gpu_info = data.get("gpu_info")
            auth_token = data.get("auth_token")

            # Validate JWT and get user
            user_id = await self._validate_token(auth_token)
            if not user_id:
                await self.send(json.dumps({
                    "type": "auth_error",
                    "error": "Invalid or expired token. Please re-login."
                }, ensure_ascii=False))
                await self.close()
                return

            self.auth_token = auth_token
            self.provider_user_id = user_id
            logger.info(
                "Registering Node: %s (user_id=%s)", self.node_id, user_id,
            )

            username = await self._register_node(self.node_id, gpu_info, user_id)
            await self.send(json.dumps({
                "type": "registered",
                "status": "ok",
                "owner": username
            }, ensure_ascii=False))
            await self._broadcast_dashboard_update()
            await self.channel_layer.group_send(
                f"user_{user_id}",
                {
                    "type": "dashboard_update",
                    "data": {"type": "refresh_provider_stats"}
                }
            )

        elif msg_type == "job_result":
            result = data.get("result", {})
            task_id = result.get("task_id")
            status = result.get("status", "failed")
            response_text = result.get("response", "")
            error = result.get("error", "")

            logger.info(
                "Job Result Received for Task %s: %s", task_id, status,
            )

            if task_id:
                if status == "success":
                    await self._complete_job(task_id, {"output": response_text}, self.provider_user_id)
                    await self._broadcast_dashboard_update()
                    # Notify involved users (Owner & Provider)
                    await self._notify_job_completion(task_id, self.provider_user_id)
                else:
                    await self._fail_job(task_id, {"error": error})
                    await self._notify_job_completion(task_id, self.provider_user_id)

        elif msg_type == "pong":
            pass

    async def _notify_job_completion(self, job_id, provider_id):
        """Send private updates to Job Owner and Provider."""
        # Async wrapper to gather data and send group messages
        data = await self._get_job_completion_data(job_id, provider_id)
        if not data:
            return

        owner_id = data['owner_id']
        job_data = data['job_data']
        owner_balance = data['owner_balance']

        # 1. Notify Job Owner (Job status + Balance update + Transaction history refresh)
        if owner_id:
            await self.channel_layer.group_send(
                f"user_{owner_id}",
                {
                    "type": "dashboard_update",
                    "data": {
                        "type": "job_update",
                        "job": job_data
                    }
                }
            )
            await self.channel_layer.group_send(
                f"user_{owner_id}",
                {
                    "type": "dashboard_update",
                    "data": {
                        "type": "balance_update",
                        "balance": str(owner_balance)
                    }
                }
            )
            # Refresh provider stats (which includes transaction history) for consumer
            await self.channel_layer.group_send(
                f"user_{owner_id}",
                {
                    "type": "dashboard_update",
                    "data": {
                        "type": "refresh_provider_stats"
                    }
                }
            )

        # 2. Notify Provider (Balance update + Transaction history refresh)
        if provider_id:
            await self.channel_layer.group_send(
                f"user_{provider_id}",
                {
                    "type": "dashboard_update",
                    "data": {
                        "type": "refresh_provider_stats"
                    }
                }
            )

    @database_sync_to_async
    def _get_job_completion_data(self, job_id, provider_id):
        """Gather job, owner, and provider data for completion notifications."""
        from .models import Job  # pylint: disable=import-outside-toplevel
        from core.models import User  # pylint: disable=import-outside-toplevel
        try:
            job = Job.objects.get(id=job_id)
            owner = job.user

            provider_bal = Decimal("0.00")
            if provider_id:
                try:
                    provider_bal = User.objects.get(
                        id=provider_id,
                    ).wallet_balance
                except Exception:  # pylint: disable=broad-except
                    pass

            input_data = job.input_data or {}
            is_dict = isinstance(input_data, dict)
            return {
                "owner_id": owner.id,
                "owner_balance": owner.wallet_balance,
                "provider_balance": provider_bal,
                "max_retries": 1,
                "job_data": {
                    "id": job.id,
                    "status": job.status,
                    "prompt": (
                        input_data.get("prompt", "")
                        if is_dict else str(input_data)
                    ),
                    "model": (
                        input_data.get("model", "")
                        if is_dict else "unknown"
                    ),
                    "cost": str(job.cost) if job.cost else None,
                    "result": job.result,
                    "created_at": str(job.created_at),
                    "completed_at": (
                        str(job.completed_at)
                        if job.completed_at else None
                    ),
                },
            }
        except Job.DoesNotExist:
            return None

    async def job_dispatch(self, event):
        """Handler for sending a job to this consumer."""
        # Only dispatch to registered nodes
        if not self.provider_user_id:
            return

        job_data = event["job_data"]

        # Prevent self-infrastructure usage
        if job_data.get("owner_id") == self.provider_user_id:
            logger.info(
                "Skipping job %s — provider is the owner.",
                job_data["task_id"],
            )
            return

        await self.send(json.dumps({
            "type": "job_dispatch",
            "job_data": job_data
        }, ensure_ascii=False))

    # --- DB Operations ---

    @database_sync_to_async
    def _validate_token(self, token):
        """Validate an agent token (gpc_...) and return user_id, or None."""
        if not token:
            return None
        try:
            from core.models import AgentToken  # pylint: disable=import-outside-toplevel
            agent_token = AgentToken.validate(token)
            if agent_token:
                return agent_token.user_id
            return None
        except Exception as e:  # pylint: disable=broad-except
            logger.warning("Token validation failed: %s", e)
            return None

    @database_sync_to_async
    def _register_node(self, node_id, gpu_info, user_id):
        """Create or update a Node record for the connecting provider."""
        from .models import Node  # pylint: disable=import-outside-toplevel
        from core.models import User  # pylint: disable=import-outside-toplevel
        owner = User.objects.get(id=user_id)
        node, created = Node.objects.update_or_create(
            node_id=node_id,
            defaults={
                "owner": owner,
                "name": f"Node-{node_id}",
                "gpu_info": gpu_info or {},
                "is_active": True,
            }
        )
        action = "Created" if created else "Updated"
        logger.info("%s Node: %s (owner: %s)", action, node, owner.username)
        return owner.username

    @database_sync_to_async
    def _mark_node_inactive(self, node_id):
        """Set a node to inactive when its WebSocket disconnects."""
        from .models import Node  # pylint: disable=import-outside-toplevel
        Node.objects.filter(node_id=node_id).update(is_active=False)
        logger.info("Node %s marked inactive", node_id)

    @database_sync_to_async
    def _touch_node_heartbeat(self, node_id):
        """Update node's last_heartbeat to keep it active."""
        from .models import Node  # pylint: disable=import-outside-toplevel
        try:
            node = Node.objects.get(node_id=node_id)
            node.save()  # Triggers auto_now on last_heartbeat
        except Node.DoesNotExist:
            logger.warning("Node %s not found for heartbeat touch", node_id)

    @database_sync_to_async
    def _complete_job(self, task_id, result_data, provider_user_id):
        """Mark a job as COMPLETED, credit provider, debit consumer."""
        from .models import Job  # pylint: disable=import-outside-toplevel
        from core.models import User  # pylint: disable=import-outside-toplevel
        from payments.models import CreditLog  # pylint: disable=import-outside-toplevel
        try:
            job = Job.objects.get(id=task_id)
            job.status = "COMPLETED"
            job.result = result_data
            job.completed_at = timezone.now()
            job.cost = JOB_COST
            job.save()

            # Credit the provider
            if provider_user_id:
                try:
                    provider = User.objects.get(id=provider_user_id)
                    provider.wallet_balance += PROVIDER_SHARE
                    provider.save()
                    model_name = job.input_data.get(
                        "model", "unknown",
                    )
                    CreditLog.objects.create(
                        user=provider,
                        amount=PROVIDER_SHARE,
                        description=(
                            f"Earned: Job #{task_id} completed"
                            f" (model: {model_name})"
                        ),
                    )
                    CreditLog.objects.get_or_create(
                        user=job.user,
                        amount=-JOB_COST,
                        description=(
                            f"Spent: Job #{task_id}"
                            f" (model: {model_name})"
                        ),
                        defaults={"created_at": job.created_at},
                    )
                    logger.info(
                        "Provider %s earned $%s for Job %s",
                        provider.username, PROVIDER_SHARE, task_id,
                    )
                except User.DoesNotExist:
                    logger.error(
                        "Provider user %s not found", provider_user_id,
                    )

            logger.info("Job %s completed successfully", task_id)
        except Job.DoesNotExist:
            logger.error("Job %s not found", task_id)

    @database_sync_to_async
    def _fail_job(self, task_id, error_data):
        """Mark a job as FAILED with error details."""
        from .models import Job  # pylint: disable=import-outside-toplevel
        try:
            job = Job.objects.get(id=task_id)
            job.status = "FAILED"
            job.result = error_data
            job.completed_at = timezone.now()
            job.save()
            logger.error("Job %s failed: %s", task_id, error_data)
        except Job.DoesNotExist:
            logger.error("Job %s not found", task_id)

class DashboardConsumer(AsyncWebsocketConsumer):
    """Sends real-time dashboard updates to authenticated frontend users."""

    async def connect(self):
        """Join public + private groups, authenticate, and send initial state."""
        self.user_id = None
        self.group_name = "dashboard_updates"

        # 1. Join public group
        await self.channel_layer.group_add(
            self.group_name,
            self.channel_name
        )

        # 2. Authenticate User (via query param ?token=...)
        query_string = self.scope.get("query_string", b"").decode("utf-8")
        params = dict(
            qs.split("=") for qs in query_string.split("&") if "=" in qs
        )
        token = params.get("token")

        if token:
            user = await self._get_user_from_token(token)
            if user:
                self.user_id = user.id
                self.user_group = f"user_{user.id}"
                await self.channel_layer.group_add(
                    self.user_group,
                    self.channel_name
                )
                logger.info(
                    "Dashboard WS: User %s connected", user.username,
                )

        self.provider_days = 30
        await self.accept()

        # 3. Send Initial Public Snapshot
        stats = await self._get_stats()
        models = await self._get_models()
        await self.send(json.dumps({
            "type": "stats_update",
            "stats": stats
        }))
        await self.send(json.dumps({
            "type": "models_update",
            "models": models
        }))

        # 4. Send Initial User Snapshot (if auth)
        if self.user_id:
            balance = await self._get_balance(self.user_id)
            await self.send(json.dumps({
                "type": "balance_update",
                "balance": str(balance)
            }))
            # Job history could be served here or fetched via REST initially.
            jobs = await self._get_recent_jobs(self.user_id)
            await self.send(json.dumps({
                "type": "jobs_update",
                "jobs": jobs
            }, default=str))

            # 5. Send Initial Provider Stats
            provider_stats = await self._get_provider_stats_async(self.user_id, self.provider_days)
            await self.send(json.dumps({
                "type": "provider_stats_update",
                "stats": provider_stats
            }))

    async def disconnect(self, close_code):
        """Leave groups on WebSocket disconnect."""
        await self.channel_layer.group_discard(
            self.group_name,
            self.channel_name
        )
        if self.user_id:
            await self.channel_layer.group_discard(
                self.user_group,
                self.channel_name
            )

    async def receive(self, text_data):
        """Handle incoming messages (e.g. subscribe_provider_stats)."""
        try:
            data = json.loads(text_data)
            msg_type = data.get("type")

            if msg_type == "subscribe_provider_stats":
                self.provider_days = int(data.get("days", 30))
                if self.user_id:
                    stats = await self._get_provider_stats_async(
                        self.user_id, self.provider_days,
                    )
                    await self.send(json.dumps({
                        "type": "provider_stats_update",
                        "stats": stats
                    }))
        except Exception as e:  # pylint: disable=broad-except
            logger.error("DashboardConsumer receive error: %s", e)

    async def dashboard_update(self, event):
        """Handle broadcast messages (public or private)."""
        msg = event["data"]

        # If this is a trigger to refresh provider stats, calculate locally
        if msg.get("type") == "refresh_provider_stats" and self.user_id:
            stats = await self._get_provider_stats_async(
                self.user_id, self.provider_days,
            )
            await self.send(json.dumps({
                "type": "provider_stats_update",
                "stats": stats
            }))
            return

        await self.send(json.dumps(msg, default=str))

    @database_sync_to_async
    def _get_user_from_token(self, token):
        """Validate a JWT access token and return the user, or None."""
        from rest_framework_simplejwt.tokens import AccessToken  # pylint: disable=import-outside-toplevel
        from core.models import User  # pylint: disable=import-outside-toplevel
        try:
            access_token = AccessToken(token)
            user_id = access_token.payload.get("user_id")
            return User.objects.get(id=user_id)
        except Exception:
            return None

    @database_sync_to_async
    def _get_balance(self, user_id):
        """Return the wallet balance for the given user."""
        from core.models import User  # pylint: disable=import-outside-toplevel
        try:
            return User.objects.get(id=user_id).wallet_balance
        except Exception:  # pylint: disable=broad-except
            return Decimal("0.00")

    @database_sync_to_async
    def _get_recent_jobs(self, user_id):
        """Return the 10 most recent jobs for the given user."""
        from .models import Job  # pylint: disable=import-outside-toplevel
        jobs = Job.objects.filter(
            user_id=user_id,
        ).order_by('-created_at')[:10]
        result = []
        for job in jobs:
            input_data = job.input_data or {}
            is_dict = isinstance(input_data, dict)
            result.append({
                "id": job.id,
                "status": job.status,
                "prompt": (
                    input_data.get("prompt", "")
                    if is_dict else str(input_data)
                ),
                "model": (
                    input_data.get("model", "")
                    if is_dict else "unknown"
                ),
                "cost": str(job.cost) if job.cost else None,
                "result": job.result,
                "created_at": str(job.created_at),
                "completed_at": (
                    str(job.completed_at)
                    if job.completed_at else None
                ),
            })
        return result

    @database_sync_to_async
    def _get_stats(self):
        """Return network stats for the dashboard."""
        from .models import Node, Job  # pylint: disable=import-outside-toplevel
        _cleanup_stale_nodes()
        active_nodes = Node.objects.filter(is_active=True).count()
        completed_jobs = Job.objects.filter(status="COMPLETED").count()
        available = self._get_models_sync()
        return {
            "active_nodes": active_nodes,
            "completed_jobs": completed_jobs,
            "available_models": len(available)
        }

    @database_sync_to_async
    def _get_models(self):
        """Return available models aggregated from active nodes."""
        _cleanup_stale_nodes()
        return self._get_models_sync()

    def _get_models_sync(self):
        """Synchronous helper: aggregate model counts from active nodes."""
        from .models import Node  # pylint: disable=import-outside-toplevel
        nodes = Node.objects.filter(is_active=True)
        model_counts = {}
        for node in nodes:
            info = node.gpu_info or {}
            node_models = info.get("models", [])
            for m in node_models:
                if isinstance(m, dict):
                    name = m.get("name")
                else:
                    name = m

                if name:
                    model_counts[name] = model_counts.get(name, 0) + 1

        return [
            {"name": k, "providers": v}
            for k, v in model_counts.items()
        ]

    @database_sync_to_async
    def _get_provider_stats_async(self, user_id, days):
        """Fetch provider statistics for the given user."""
        from core.models import User  # pylint: disable=import-outside-toplevel
        from .utils import get_provider_stats  # pylint: disable=import-outside-toplevel
        try:
            user = User.objects.get(id=user_id)
            return get_provider_stats(user, days)
        except Exception as e:  # pylint: disable=broad-except
            logger.error("Error getting provider stats: %s", e)
            return None
