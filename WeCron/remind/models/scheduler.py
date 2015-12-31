#coding: utf-8
from __future__ import unicode_literals, absolute_import
import logging
from datetime import timedelta

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.util import timedelta_seconds
from django.utils import timezone
from django.db import transaction
from .remind import Remind

logger = logging.getLogger(__name__)


class RemindScheduler(BackgroundScheduler):
    misfire_grace_time = 60
    MAX_WAIT_TIME = 60*60  # wake up every hour

    def _process_jobs(self):
        """Goodbye you apscheduler"""
        logger.debug('Looking for jobs to run')
        now = timezone.now()
        grace_time = timedelta(seconds=self.misfire_grace_time)

        with self._jobstores_lock:
            with transaction.atomic():
                # Lock the row
                for rem in Remind.objects.select_for_update().filter(
                        status='pending', time__range=(now-grace_time, now)).all():
                    rem.notify_users()
                    rem.status = 'done'
                    rem.save()
                next_remind = Remind.objects.filter(time__gt=now).order_by('time').first()
                wait_seconds = None
                if next_remind:
                    wait_seconds = max(timedelta_seconds(next_remind.time - timezone.now()), 0)
                    logger.debug('Next wakeup is due at %s (in %f seconds)', next_remind.time.isoformat(), wait_seconds)
                else:
                    logger.debug('No jobs; waiting until a job is added')
                return wait_seconds


# import sys, socket
#
# try:
#     sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
#     sock.bind(("127.0.0.1", 47200))
# except socket.error:
#     print "!!!scheduler already started, DO NOTHING"
# else:
#     from apscheduler.schedulers.background import BackgroundScheduler
#     scheduler = BackgroundScheduler()
#     scheduler.start()
#     print "scheduler started"
# http://stackoverflow.com/questions/16053364


# @atexit.register
# def shutdown_scheduler():
#     logger.info('Shutting down scheduler')
#     scheduler.shutdown()


# @scheduler.scheduled_job('cron', hour=3, jobstore='default', timezone=settings.TIME_ZONE)
# def update_user_info():
#     print "+"*10, 'updating user info'
#
#
# @scheduler.scheduled_job('cron', hour=4, jobstore='default', timezone=settings.TIME_ZONE)
# def remove_outdated_reminds():
#     print '-'*10, 'removing outdated reminds'

