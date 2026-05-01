"""
celery_app.py
=============
Celery application instance configured with Redis as broker and backend.

Start worker:
    celery -A core.celery_app worker --loglevel=info

Start beat (scheduled tasks):
    celery -A core.celery_app beat --loglevel=info
"""

import os
from celery import Celery

# Redis connection — defaults to localhost for dev, override via env for prod
REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379")

app = Celery(
    "sma_enterprise",
    broker=f"{REDIS_URL}/0",
    backend=f"{REDIS_URL}/1",
)

# ── celery config ───────────────────────────────────────────────
app.conf.update(
    # Serialization
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",

    # Tracking
    task_track_started=True,         # report STARTED state (not just PENDING → SUCCESS)
    result_expires=3600,             # results expire after 1 hour

    # Reliability
    task_acks_late=True,             # ack AFTER task completes (crash safety)
    worker_prefetch_multiplier=1,    # one task at a time per worker (downloads are heavy)

    # Timezone
    timezone="UTC",
    enable_utc=True,
)

# Auto-discover tasks in these modules
app.autodiscover_tasks([
    "services.resources_downloader",
    "services.scheduler",
    "services.media",
])

# ── celery beat schedule ────────────────────────────────────────
app.conf.beat_schedule = {
    "check-pending-posts-every-minute": {
        "task": "scheduler.check_pending",
        "schedule": 60.0,  # every 60 seconds
    },
}
