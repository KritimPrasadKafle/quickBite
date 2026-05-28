from celery import Celery

celery_app = Celery(
    "quickbite",
    broker = "redis://localhost:6379/0",
    backend = "redis://localhost:6379/0",
    include = ["core.tasks"],
)

celery_app.conf.update(
    task_serializer="json",
    result_serializer="json",
    accept_content=["json"],
    timezone="Asia/Kathmandu",
    enable_utc=True,
    task_acks_late=True,         
    task_max_retries=3,           
)