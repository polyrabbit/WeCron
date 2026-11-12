#coding: utf-8
import logging
from datetime import timedelta

from apscheduler.schedulers.background import BackgroundScheduler
from django.utils import timezone
from django.db import close_old_connections, connections, transaction
from .remind import Remind

logger = logging.getLogger(__name__)


class RemindScheduler(BackgroundScheduler):
    misfire_grace_time = 5 * 60
    MAX_WAIT_TIME = 60*60  # wake up every hour
    RETRY_WAIT_TIME = 30
    MISSED_LOOKBACK = timedelta(days=7)
    _swept_until = None

    def _process_jobs(self):
        """Goodbye you apscheduler"""
        logger.debug('Looking for jobs to run')
        close_old_connections() # close obsolete connections before processing jobs to avoid "InterfaceError: connection already closed" error
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
                # A separate transaction locking in the same notify_time order, so two workers won't deadlock
                with transaction.atomic():
                    self.reschedule_missed(now - grace_time)
                next_remind = Remind.objects.filter(
                    done=False, notify_time__gt=now-grace_time).order_by('notify_time').first()
                if next_remind:
                    wait_seconds = max((next_remind.notify_time - timezone.now()).total_seconds(), 0)
                    logger.debug('Next wake up is due at %s (in %f seconds)', next_remind.notify_time.isoformat(), wait_seconds)
                    # Event.wait() overflows on far future reminders
                    return min(wait_seconds, self.MAX_WAIT_TIME)
                logger.debug('No jobs, waiting until a job is added')
        # This is a vital thread, DO NOT die
        except Exception:
            logger.exception('Error running scheduler job')
            connections.close_all()
            # The sweep was rolled back, start it over. Retrying soon won't send twice, notifications go out on commit
            self._swept_until = None
            return self.RETRY_WAIT_TIME
        # APScheduler 3.x waits forever on None, so poll at least hourly
        return self.MAX_WAIT_TIME

    def reschedule_missed(self, until):
        """Repeating reminds missed during downtime would never fire again, move them to the next occurrence"""
        since = self._swept_until or until - self.MISSED_LOOKBACK
        missed = Remind.objects.select_for_update().filter(
            done=False, notify_time__gte=since, notify_time__lt=until).exclude(repeat={}).order_by('notify_time')
        for rem in missed:
            if rem.has_repeat():
                rem.save()  # the pre_save hook skips the missed occurrences without notifying
                logger.info('Rescheduled missed remind %s to %s', rem.pk.hex, rem.notify_time.isoformat())
        self._swept_until = until
