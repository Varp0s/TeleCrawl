from __future__ import absolute_import, unicode_literals
import os
from celery import Celery
from django.conf import settings

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'telecrawl.settings')
app = Celery('telecrawl')
app.config_from_object('django.conf:settings', namespace='CELERY')
app.autodiscover_tasks()

from celery.schedules import crontab
app.conf.beat_schedule = {
    'clean-irrelevant-messages': {
        'task': 'crawler.tasks.clean_irrelevant_messages',
        'schedule': crontab(hour=0, minute=0), 
    },
    'archive-github-urls': {
        'task': 'crawler.tasks.archive_github_urls',
        'schedule': crontab(minute='*/30'), 
    },
}
app.conf.timezone = 'Europe/Istanbul'

@app.task(bind=True)
def debug_task(self):
    print(f'Request: {self.request!r}')
