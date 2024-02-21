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
    misfire_grace_time = 5 * 60
    MAX_WAIT_TIME = 60*60  # wake up every hour

    def _process_jobs(self):
        """Goodbye you apscheduler"""
        logger.debug('Looking for jobs to run')
        try:
            now = timezone.now()
            grace_time = timedelta(seconds=self.misfire_grace_time)

            with self._jobstores_lock:
                with transaction.atomic():
                    # Use select_for_update inside a transaction to lock the row
                    # Statically store the select result, in case of modifying the result in selection,
                    # which will results in a infinite selection.
                    remind_list = list(Remind.objects.select_for_update().filter(
                        done=False, notify_time__range=(now - grace_time, now)).order_by('notify_time').all())
                    for rem in remind_list:
                        try:
                            rem.notify_users()
                        finally:
                            rem.done = True
                            rem.save()
                    next_remind = Remind.objects.filter(
                        done=False, notify_time__gt=now-grace_time).order_by('notify_time').first()
                    wait_seconds = None
                    if next_remind:
                        wait_seconds = max(timedelta_seconds(next_remind.notify_time - timezone.now()), 0)
                        logger.debug('Next wake up is due at %s (in %f seconds)', next_remind.notify_time.isoformat(), wait_seconds)
                    else:
                        logger.debug('No jobs, waiting until a job is added')
                    return wait_seconds
        # This is a vital thread, DO NOT die
        except Exception as e:
            logger.exception('Error running scheduler job')

