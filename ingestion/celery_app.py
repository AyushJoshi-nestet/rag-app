from celery import Celery

app = Celery('celery_app', broker='redis://localhost:6379/0', backend='redis://localhost:6379/1')

app.conf.update(
    task_serializer='json',
    accept_content=['json'],  # Ignore other content
    result_serializer='json',
    timezone='Europe/Oslo',
    enable_utc=True,
)
