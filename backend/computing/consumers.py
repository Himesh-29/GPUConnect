import asyncio
import json
import logging
from channels.generic.websocket import AsyncWebsocketConsumer
from channels.db import database_sync_to_async
from django.utils import timezone
from decimal import Decimal

logger = logging.getLogger(__name__)

JOB_COST = Decimal("1.00")
PROVIDER_SHARE = Decimal("0.80")  # Provider gets 80% of job cost


class GPUConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        self.node_id = "unknown"
        self.provider_user_id = None  # Will be set after JWT validation
        self.group_name = "gpu_nodes"
        await self.channel_layer.group_add(
            self.group_name,
            self.channel_name
        )
        await self.accept()
        logger.info("WebSocket Connected")
        self._ping_task = asyncio.ensure_future(self._keep_alive())

    async def _keep_alive(self):
        """Send periodic pings to keep the WebSocket alive during long inference."""
        try:
            while True:
                await asyncio.sleep(15)
                await self.send(json.dumps({"type": "ping"}, ensure_ascii=False))
        except Exception:
            pass

    async def disconnect(self, close_code):
        logger.info(f"WebSocket Disconnected: {close_code}")
        if hasattr(self, '_ping_task'):
            self._ping_task.cancel()
        await self.channel_layer.group_discard(
            self.group_name,
            self.channel_name
        )
        if self.node_id != "unknown":
            await self._mark_node_inactive(self.node_id)

    async def receive(self, text_data):
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

            self.provider_user_id = user_id
            logger.info(f"Registering Node: {self.node_id} (user_id={user_id})")

            username = await self._register_node(self.node_id, gpu_info, user_id)
            await self.send(json.dumps({
                "type": "registered",
                "status": "ok",
                "owner": username
            }, ensure_ascii=False))

        elif msg_type == "job_result":
            result = data.get("result", {})
            task_id = result.get("task_id")
            status = result.get("status", "failed")
            response_text = result.get("response", "")
            error = result.get("error", "")

            logger.info(f"Job Result Received for Task {task_id}: {status}")

            if task_id:
                if status == "success":
                    await self._complete_job(task_id, {"output": response_text}, self.provider_user_id)
                else:
                    await self._fail_job(task_id, {"error": error})

        elif msg_type == "pong":
            pass

    async def job_dispatch(self, event):
        """Handler for sending a job to this consumer."""
        job_data = event["job_data"]
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
            from core.models import AgentToken
            agent_token = AgentToken.validate(token)
            if agent_token:
                return agent_token.user_id
            return None
        except Exception as e:
            logger.warning(f"Token validation failed: {e}")
            return None

    @database_sync_to_async
    def _register_node(self, node_id, gpu_info, user_id):
        from .models import Node
        from core.models import User
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
        logger.info(f"{action} Node: {node} (owner: {owner.username})")
        return owner.username

    @database_sync_to_async
    def _mark_node_inactive(self, node_id):
        from .models import Node
        Node.objects.filter(node_id=node_id).update(is_active=False)
        logger.info(f"Node {node_id} marked inactive")

    @database_sync_to_async
    def _complete_job(self, task_id, result_data, provider_user_id):
        from .models import Job
        from core.models import User
        from payments.models import CreditLog
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
                    CreditLog.objects.create(
                        user=provider,
                        amount=PROVIDER_SHARE,
                        description=f"Earned: Job #{task_id} completed (model: {job.input_data.get('model', 'unknown')})"
                    )
                    # Also log the consumer debit
                    CreditLog.objects.get_or_create(
                        user=job.user,
                        amount=-JOB_COST,
                        description=f"Spent: Job #{task_id} (model: {job.input_data.get('model', 'unknown')})",
                        defaults={"created_at": job.created_at}
                    )
                    logger.info(f"💰 Provider {provider.username} earned ${PROVIDER_SHARE} for Job {task_id}")
                except User.DoesNotExist:
                    logger.error(f"Provider user {provider_user_id} not found")

            logger.info(f"Job {task_id} completed successfully")
        except Job.DoesNotExist:
            logger.error(f"Job {task_id} not found")

    @database_sync_to_async
    def _fail_job(self, task_id, error_data):
        from .models import Job
        try:
            job = Job.objects.get(id=task_id)
            job.status = "FAILED"
            job.result = error_data
            job.completed_at = timezone.now()
            job.save()
            logger.error(f"Job {task_id} failed: {error_data}")
        except Job.DoesNotExist:
            logger.error(f"Job {task_id} not found")
