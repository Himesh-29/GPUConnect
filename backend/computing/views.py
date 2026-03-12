"""Views for the computing module — job submission, listing, and stats."""
from decimal import Decimal

from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer
from django.shortcuts import get_object_or_404
from rest_framework import views, status
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.response import Response

from .models import Job, Node, ChatSession


class JobSubmissionView(views.APIView):
    """Submit a new GPU inference job."""
    permission_classes = [IsAuthenticated]

    def post(self, request):
        """Create a job, deduct credits, and dispatch to GPU nodes."""
        user = request.user

        prompt = request.data.get("prompt")
        model = request.data.get("model", "llama3.2:latest")
        stream = request.data.get("stream", False)

        if not prompt:
            return Response(
                {"error": "Prompt is required"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Ensure there are active nodes NOT owned by this user
        other_nodes = Node.objects.filter(is_active=True).exclude(owner=user)
        if not other_nodes.exists():
            return Response(
                {"error": "No available third-party nodes. "
                 "You cannot serve your own requests."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Check Balance (1.00 base + 0.05 surcharge for streaming)
        job_cost = Decimal('1.05') if stream else Decimal('1.00')
        if user.wallet_balance < job_cost:
            return Response(
                {"error": "Insufficient funds"},
                status=status.HTTP_402_PAYMENT_REQUIRED,
            )

        user.wallet_balance -= job_cost
        user.save()

        session_id = request.data.get("session_id")
        session = None
        if session_id:
            try:
                session = ChatSession.objects.get(id=session_id, user=user)
            except ChatSession.DoesNotExist:
                return Response(
                    {"error": "Session not found or forbidden."},
                    status=status.HTTP_404_NOT_FOUND,
                )

        job = Job.objects.create(
            user=user,
            session=session,
            task_type="inference",
            input_data={"prompt": prompt, "model": model, "stream": stream},
            status="PENDING",
            cost=job_cost,
        )

        # If session name is default, we can optionally auto-update it here
        if session and session.name == 'New Chat':
            session.name = prompt[:30] + ('...' if len(prompt) > 30 else '')
            session.save()

        # Dispatch to all connected GPU provider nodes
        channel_layer = get_channel_layer()
        async_to_sync(channel_layer.group_send)(
            "gpu_nodes",
            {
                "type": "job_dispatch",
                "job_data": {
                    "task_id": job.id,
                    "owner_id": user.id,
                    "model": model,
                    "prompt": prompt,
                    "stream": stream
                }
            }
        )

        return Response({"status": "submitted", "job_id": job.id}, status=status.HTTP_201_CREATED)


class JobDetailView(views.APIView):
    """Retrieve details for a single job."""
    permission_classes = [IsAuthenticated]

    def get(self, request, job_id):
        """Return job details if the requesting user owns the job."""
        job = get_object_or_404(Job, id=job_id)
        if job.user != request.user:
            return Response({"error": "Unauthorized"}, status=status.HTTP_403_FORBIDDEN)

        return Response({
            "id": job.id,
            "session_id": job.session_id,
            "status": job.status,
            "result": job.result,
            "prompt": job.input_data.get("prompt"),
            "model": job.input_data.get("model"),
            "cost": str(job.cost) if job.cost else None,
            "created_at": job.created_at,
            "completed_at": job.completed_at,
        })


class JobListView(views.APIView):
    """List all jobs for the authenticated user."""
    permission_classes = [IsAuthenticated]

    def get(self, request):
        """Return all jobs belonging to the authenticated user."""
        jobs = Job.objects.filter(user=request.user).order_by('-created_at')
        data = [{
            "id": j.id,
            "session_id": j.session_id,
            "status": j.status,
            "prompt": j.input_data.get("prompt", "")[:80],
            "model": j.input_data.get("model", ""),
            "cost": str(j.cost) if j.cost else None,
            "result": j.result,
            "created_at": j.created_at,
            "completed_at": j.completed_at,
        } for j in jobs]
        return Response(data)


class AvailableModelsView(views.APIView):
    """Returns models available across all active nodes.
    
    Public endpoint — consumers can browse what's available before signing up.
    """
    permission_classes = [AllowAny]

    def get(self, _request):
        """Return models available across all active nodes."""
        active_nodes = Node.objects.filter(is_active=True)
        model_map = {}

        for node in active_nodes:
            models = node.gpu_info.get("models", [])
            for m in models:
                if m not in model_map:
                    model_map[m] = {
                        "name": m,
                        "providers": 0,
                        "nodes": [],
                    }
                model_map[m]["providers"] += 1
                model_map[m]["nodes"].append(node.node_id)

        models_list = sorted(model_map.values(), key=lambda x: -x["providers"])
        return Response({
            "models": models_list,
            "total_nodes": active_nodes.count(),
        })


class NetworkStatsView(views.APIView):
    """Public endpoint for network statistics."""
    permission_classes = [AllowAny]

    def get(self, _request):
        """Return public network-wide statistics."""
        active_nodes = Node.objects.filter(is_active=True).count()
        total_jobs = Job.objects.count()
        completed_jobs = Job.objects.filter(status="COMPLETED").count()

        # Collect unique models
        all_models = set()
        for node in Node.objects.filter(is_active=True):
            for m in node.gpu_info.get("models", []):
                all_models.add(m)

        return Response({
            "active_nodes": active_nodes,
            "total_jobs": total_jobs,
            "completed_jobs": completed_jobs,
            "available_models": len(all_models),
        })


class ProviderStatsView(views.APIView):
    """Authenticated endpoint returning comprehensive provider metrics."""
    permission_classes = [IsAuthenticated]

    def get(self, request):
        """Return comprehensive provider metrics for the current user."""
        from .utils import get_provider_stats  # pylint: disable=import-outside-toplevel
        days = int(request.query_params.get("days", 30))
        stats = get_provider_stats(request.user, days)
        return Response(stats)


class SessionListView(views.APIView):
    """List and create Chat Sessions."""
    permission_classes = [IsAuthenticated]

    def get(self, request):
        sessions = ChatSession.objects.filter(user=request.user).order_by('-created_at')
        data = []
        for s in sessions:
            jobs = list(s.jobs.order_by('created_at').values(
                'id', 'status', 'input_data', 'result', 'cost', 'created_at', 'completed_at'
            ))
            # Format jobs slightly
            formatted_jobs = []
            for j in jobs:
                formatted_jobs.append({
                    "id": j['id'],
                    "status": j['status'],
                    "prompt": j['input_data'].get('prompt', ''),
                    "model": j['input_data'].get('model', ''),
                    "cost": str(j['cost']) if j['cost'] else None,
                    "result": j['result'],
                    "created_at": j['created_at'],
                    "completed_at": j['completed_at'],
                })
            
            data.append({
                "id": str(s.id),
                "name": s.name,
                "created_at": s.created_at,
                "jobs": formatted_jobs,
            })
        return Response(data)

    def post(self, request):
        name = request.data.get("name", "New Chat")
        session = ChatSession.objects.create(user=request.user, name=name)
        return Response({
            "id": str(session.id),
            "name": session.name,
            "created_at": session.created_at,
            "jobs": []
        }, status=status.HTTP_201_CREATED)


class SessionDetailView(views.APIView):
    """Retrieve, update or delete a specific Chat Session."""
    permission_classes = [IsAuthenticated]

    def patch(self, request, session_id):
        session = get_object_or_404(ChatSession, id=session_id)
        if session.user != request.user:
            return Response({"error": "Unauthorized"}, status=status.HTTP_403_FORBIDDEN)
        
        name = request.data.get("name")
        if name:
            session.name = name
            session.save()
            return Response({"status": "success", "name": session.name})
        return Response({"error": "No name provided"}, status=status.HTTP_400_BAD_REQUEST)

    def delete(self, request, session_id):
        session = get_object_or_404(ChatSession, id=session_id)
        if session.user != request.user:
            return Response({"error": "Unauthorized"}, status=status.HTTP_403_FORBIDDEN)
        
        session.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)
