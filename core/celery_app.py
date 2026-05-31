from celery import Celery
from core.config import settings

celery_app = Celery(
    "quickbite",
    broker=settings.RABBITMQ_URL,
    backend=settings.REDIS_URL,
    include=["core.tasks"],
)

celery_app.conf.update(
    task_serializer="json",
    result_serializer="json",
    accept_content=["json"],
    timezone="Asia/Kathmandu",
    enable_utc=True,
    task_acks_late=True,
    task_queues={
        "high_priority": {
            "exchange": "high_priority",
            "routing_key": "high_priority",
        },
        "celery": {
            "exchange": "celery",
            "routing_key": "celery",
        },
    },
    task_default_queue="celery",
    task_routes={
        "tasks.send_reset_email": {"queue": "high_priority"},
    },
)