web: gunicorn --timeout 120 --preload app:app
worker: celery -A tasks worker --loglevel=info -P gevent --concurrency=20 --max-tasks-per-child=1
