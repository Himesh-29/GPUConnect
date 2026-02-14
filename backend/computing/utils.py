"""Utility functions for computing module statistics and metrics."""
import datetime
from decimal import Decimal

from django.db.models import Count, Sum
from django.db.models.functions import TruncDate
from django.utils import timezone

from payments.models import CreditLog
from .models import Job, Node


def get_provider_stats(user, days=30):  # pylint: disable=too-many-locals
    """
    Calculates comprehensive provider and consumer metrics for a user.
    Reusable by both REST views and WebSocket consumers.
    """
    since = timezone.now() - datetime.timedelta(days=days)

    # --- Provider Nodes ---
    my_nodes = Node.objects.filter(owner=user)
    active_nodes = my_nodes.filter(is_active=True)

    # --- Jobs Served (jobs completed on my nodes) ---
    jobs_served = Job.objects.filter(
        node__owner=user,
        status="COMPLETED"
    )
    jobs_served_period = jobs_served.filter(completed_at__gte=since)

    # --- Earnings ---
    earnings_logs = CreditLog.objects.filter(
        user=user,
        amount__gt=0,
        description__startswith="Earned:"
    )
    total_earnings = earnings_logs.aggregate(total=Sum("amount"))["total"] or Decimal("0.00")
    period_earnings = earnings_logs.filter(
        created_at__gte=since
    ).aggregate(total=Sum("amount"))["total"] or Decimal("0.00")

    # --- Spending (as consumer) ---
    spending_logs = CreditLog.objects.filter(
        user=user,
        amount__lt=0
    )
    total_spent = abs(spending_logs.aggregate(total=Sum("amount"))["total"] or Decimal("0.00"))

    # --- Earnings over time ---
    earnings_by_day = list(
        earnings_logs.filter(created_at__gte=since)
        .annotate(date=TruncDate("created_at"))
        .values("date")
        .annotate(earned=Sum("amount"), jobs=Count("id"))
        .order_by("date")
    )
    for entry in earnings_by_day:
        entry["date"] = entry["date"].isoformat()
        entry["earned"] = float(entry["earned"])

    # --- Per-model breakdown ---
    model_stats = {}
    for job in jobs_served_period:
        model = "unknown"
        if isinstance(job.input_data, dict):
            model = (job.input_data or {}).get("model", "unknown")
        if model not in model_stats:
            model_stats[model] = {"model": model, "jobs": 0, "earned": 0.0}
        model_stats[model]["jobs"] += 1
        model_stats[model]["earned"] += 0.80  # PROVIDER_SHARE

    # --- Recent transactions ---
    recent_logs = CreditLog.objects.filter(user=user).order_by("-created_at")[:50]
    transactions = [{
        "id": log.id,
        "amount": float(log.amount),
        "description": log.description,
        "created_at": log.created_at.isoformat(),
        "type": "earning" if log.amount > 0 else "spending"
    } for log in recent_logs]

    # --- Jobs I submitted (as consumer) ---
    my_jobs = Job.objects.filter(user=user).order_by('-created_at')
    consumer_jobs = []
    for j in my_jobs[:50]:
        prompt = ""
        model = "unknown"
        if isinstance(j.input_data, dict):
            prompt = (j.input_data or {}).get("prompt", "")[:80]
            model = (j.input_data or {}).get("model", "")
        else:
            prompt = str(j.input_data)[:80]
        consumer_jobs.append({
            "id": j.id,
            "status": j.status,
            "prompt": prompt,
            "model": model,
            "cost": str(j.cost) if j.cost else None,
            "result": j.result,
            "created_at": j.created_at.isoformat(),
            "completed_at": (
                j.completed_at.isoformat() if j.completed_at else None
            ),
        })

    return {
        "provider": {
            "total_earnings": float(total_earnings),
            "period_earnings": float(period_earnings),
            "total_jobs_served": jobs_served.count(),
            "period_jobs_served": jobs_served_period.count(),
            "active_nodes": active_nodes.count(),
            "total_nodes": my_nodes.count(),
            "earnings_by_day": earnings_by_day,
            "model_breakdown": list(model_stats.values()),
        },
        "consumer": {
            "total_spent": float(total_spent),
            "total_jobs": my_jobs.count(),
            "jobs": consumer_jobs,
        },
        "wallet_balance": float(user.wallet_balance),
        "transactions": transactions,
        "period_days": days,
    }
