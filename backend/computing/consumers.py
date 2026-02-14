import asyncio
import json
import logging
from channels.generic.websocket import AsyncWebsocketConsumer
from channels.db import database_sync_to_async
from django.utils import timezone
from decimal import Decimal

logger = logging.getLogger(__name__)

JOB_COST = Decimal("1.00")
PROVIDER_SHARE = Decimal("1.00")  # Provider gets 100% — fully decentralized, no platform fee


class GPUConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        self.node_id = "unknown"
        self.provider_user_id = None
        self.auth_token = None  # Store token for re-validation
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
        # We re-calculate stats and broadcast. 
        # Ideally we'd just send the delta, but full refresh is safer for consistency.
        # We can implement a static helper or just duplicate logic slightly or make DashboardConsumer methods static?
        # Better: Send a "trigger" message to DashboardConsumer group telling them to refresh?
        # NO, that causes N refreshes.
        # Best: Calculate here and send.
        
        # We need to run DB queries.
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

    # Re-use the logic from DashboardConsumer by moving it to a helper or just duplicating (it's small)
    @database_sync_to_async
    def _get_stats(self):
        from .models import Node, Job
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
        return self._get_models_sync_shared()
    
    def _get_models_sync_shared(self):
        from .models import Node
        nodes = Node.objects.filter(is_active=True)
        model_counts = {}
        for node in nodes:
            info = node.gpu_info or {}
            models = info.get("models", [])
            for m in models:
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
                        logger.warning(f"Token revoked for node {self.node_id}. Disconnecting.")
                        await self.send(json.dumps({
                            "type": "auth_error",
                            "error": "Token revoked or expired."
                        }, ensure_ascii=False))
                        await self.close()
                        return

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

            self.auth_token = auth_token  # Save for keep-alive checks
            self.provider_user_id = user_id
            logger.info(f"Registering Node: {self.node_id} (user_id={user_id})")

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

            logger.info(f"Job Result Received for Task {task_id}: {status}")

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
        if not data: return

        owner_id = data['owner_id']
        job_data = data['job_data']
        owner_balance = data['owner_balance']
        provider_balance = data['provider_balance']

        # 1. Notify Job Owner (Job status + Balance update)
        if owner_id:
            await self.channel_layer.group_send(
                f"user_{owner_id}",
                {
                    "type": "dashboard_update",
                    "data": {
                        "type": "job_update", # Single job update
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

        # 2. Notify Provider (Balance update)
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
        from .models import Job
        from core.models import User
        try:
            job = Job.objects.get(id=job_id)
            owner = job.user
            
            provider_balance = Decimal("0.00")
            if provider_id:
                try:
                    provider_balance = User.objects.get(id=provider_id).wallet_balance
                except: pass

            return {
                "owner_id": owner.id,
                "owner_balance": owner.wallet_balance,
                "provider_balance": provider_balance,
                "max_retries": 1,
                "job_data": {
                    "id": job.id, "status": job.status, 
                    "prompt": (job.input_data or {}).get('prompt', '') if isinstance(job.input_data, dict) else str(job.input_data),
                    "model": (job.input_data or {}).get('model', '') if isinstance(job.input_data, dict) else "unknown", 
                    "cost": str(job.cost) if job.cost else None,
                    "result": job.result, 
                    "created_at": str(job.created_at),
                    "completed_at": str(job.completed_at) if job.completed_at else None
                }
            }
        except Job.DoesNotExist:
            return None

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

class DashboardConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        self.user_id = None
        self.group_name = "dashboard_updates"
        
        # 1. Join public group
        await self.channel_layer.group_add(
            self.group_name,
            self.channel_name
        )
        
        # 2. Authenticate User (via query param ?token=...)
        query_string = self.scope.get("query_string", b"").decode("utf-8")
        params = dict(qs.split("=") for qs in query_string.split("&") if "=" in qs)
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
                logger.info(f"Dashboard WS: User {user.username} connected")

        self.provider_days = 30 # Default
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
            # Usually REST for initial list is fine, and WS for updates.
            # But let's send recent jobs for "streaming" feeel.
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
        try:
            data = json.loads(text_data)
            msg_type = data.get("type")
            
            if msg_type == "subscribe_provider_stats":
                self.provider_days = int(data.get("days", 30))
                if self.user_id:
                    stats = await self._get_provider_stats_async(self.user_id, self.provider_days)
                    await self.send(json.dumps({
                        "type": "provider_stats_update",
                        "stats": stats
                    }))
        except Exception as e:
            logger.error(f"DashboardConsumer receive error: {e}")

    async def dashboard_update(self, event):
        """Handle broadcast messages (public or private)."""
        msg = event["data"]
        
        # If this is a generic trigger to refresh provider stats, calculate them locally for this user
        if msg.get("type") == "refresh_provider_stats" and self.user_id:
             stats = await self._get_provider_stats_async(self.user_id, self.provider_days)
             await self.send(json.dumps({
                 "type": "provider_stats_update",
                 "stats": stats
             }))
             return

        await self.send(json.dumps(msg, default=str))

    @database_sync_to_async
    def _get_user_from_token(self, token):
        from rest_framework_simplejwt.tokens import AccessToken
        from core.models import User
        try:
            access_token = AccessToken(token)
            user_id = access_token.payload.get("user_id")
            return User.objects.get(id=user_id)
        except Exception:
            return None

    @database_sync_to_async
    def _get_balance(self, user_id):
        from core.models import User
        try:
            return User.objects.get(id=user_id).wallet_balance
        except:
            return Decimal("0.00")

    @database_sync_to_async
    def _get_recent_jobs(self, user_id):
        from .models import Job
        # Return last 10 jobs
        jobs = Job.objects.filter(user_id=user_id).order_by('-created_at')[:10]
        result = []
        for job in jobs:
            result.append({
                "id": job.id,
                "status": job.status,
                "prompt": (job.input_data or {}).get("prompt", "") if isinstance(job.input_data, dict) else str(job.input_data),
                "model": (job.input_data or {}).get("model", "") if isinstance(job.input_data, dict) else "unknown",
                "cost": str(job.cost) if job.cost else None,
                "result": job.result,
                "created_at": str(job.created_at),
                "completed_at": str(job.completed_at) if job.completed_at else None
            })
        return result

    @database_sync_to_async
    def _get_stats(self):
        from .models import Node, Job
        active_nodes = Node.objects.filter(is_active=True).count()
        completed_jobs = Job.objects.filter(status="COMPLETED").count()
        models = self._get_models_sync()
        return {
            "active_nodes": active_nodes,
            "completed_jobs": completed_jobs,
            "available_models": len(models)
        }

    @database_sync_to_async
    def _get_models(self):
        return self._get_models_sync()

    def _get_models_sync(self):
        from .models import Node
        nodes = Node.objects.filter(is_active=True)
        model_counts = {}
        for node in nodes:
            info = node.gpu_info or {}
            models = info.get("models", [])
            for m in models:
                if isinstance(m, dict):
                    name = m.get("name")
                else: 
                     name = m # Handle string list if legacy
                
                if name:
                    model_counts[name] = model_counts.get(name, 0) + 1
        
        return [{"name": k, "providers": v} for k, v in model_counts.items()]

    @database_sync_to_async
    def _get_provider_stats_async(self, user_id, days):
        from core.models import User
        from .utils import get_provider_stats
        try:
            user = User.objects.get(id=user_id)
            return get_provider_stats(user, days)
        except Exception as e:
            logger.error(f"Error getting provider stats: {e}")
            return None
