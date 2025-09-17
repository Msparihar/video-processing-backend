import os
from celery import Celery

broker = os.getenv("CELERY_BROKER_URL", "amqp://guest:guest@rabbitmq:5672//")
backend = os.getenv("CELERY_RESULT_BACKEND", "redis://redis:6379/0")

# create Celery instance
celery_app = Celery("video_worker", broker=broker, backend=backend)

# Load optional settings from environment variables for namespace CELERY_
celery_app.conf.update(
    task_time_limit=int(os.getenv("CELERY_TASK_TIME_LIMIT", 0)) or None,
    task_soft_time_limit=int(os.getenv("CELERY_TASK_SOFT_TIME_LIMIT", 0)) or None,
)

# alias 'app' for Celery CLI discovery (celery -A app.celery_app ...)
app = celery_app

celery_app.autodiscover_tasks(["app.tasks"])  # discover tasks in app/tasks
celery_app.conf.task_routes = {"app.tasks.*": {"queue": os.getenv("CELERY_TASK_QUEUE", "default")}}
