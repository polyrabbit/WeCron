"""
WSGI config for wecron project.

It exposes the WSGI callable as a module-level variable named ``application``.

For more information on this file, see
https://docs.djangoproject.com/en/1.8/howto/deployment/wsgi/
"""

import os

from django.core.wsgi import get_wsgi_application

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "wecron.settings")

application = get_wsgi_application()

# Start scheduler here so it only gets started when running server
from remind.models.scheduler import RemindScheduler
from django.db.models.signals import post_save

# Remind = self.get_model('Remind')
scheduler = RemindScheduler()
post_save.connect(lambda *a, **k: scheduler.wakeup(),
                  sender='remind.Remind',
                  weak=False,
                  dispatch_uid='update-scheduler')
scheduler.start()
