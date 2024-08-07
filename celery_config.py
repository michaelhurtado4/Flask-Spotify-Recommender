from celery import Celery
import os
from dotenv import load_dotenv

load_dotenv()

celery_app = Celery('tasks', broker=os.environ.get('redis_url'), backend=os.environ.get('redis_url'))

celery_app.conf.update(
    result_expires=60,
    task_routes={
        'tasks.get_likedsongs': {'queue': 'cloud_queue'},
    },
    beat_schedule={
        'run-get-likedsongs-every-30-seconds': {
            'task': 'tasks.get_likedsongs',
            'schedule': 30.0,
        },
    },
)

celery_app.autodiscover_tasks(['tasks'])
import tasks  # Import tasks module to register tasks

# Check Redis connection
with celery_app.connection() as connection:
    connection.ensure_connection()
    print("Connected to Redis successfully")
