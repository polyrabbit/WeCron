# coding: utf-8

import datetime
from datetime import timedelta
from unittest import mock

from django.test import TestCase
from django.utils import timezone
from remind.models import Remind
from remind.models.remind import REPEAT_KEY_DAY, REPEAT_KEY_MONTH
from remind.models.scheduler import RemindScheduler
from wechat_user.models import WechatUser


class RemindModelTestCase(TestCase):

    def setUp(self):
        u = WechatUser(openid='miao', nickname='miaomiao', subscribe=True, last_login=timezone.now())
        u.save()

    def test_add_add_participant(self):
        WechatUser(openid='abc', nickname='abcabc', subscribe=True).save()
        r = Remind(time=timezone.now(), owner_id='miao', event='吃饭', desc='吃饭饭')
        r.save()
        r.add_participant('abc')
        r.add_participant('abc')

        self.assertEqual(r.participants, ['abc'])

    def test_notify_time_update(self):
        n = timezone.now()
        r = Remind(time=n, owner_id='miao', event='吃饭', desc='吃饭饭')
        r.save()
        self.assertEqual(r.notify_time, n)
        r.defer = -10
        r.save()
        self.assertEqual(r.notify_time, n - timedelta(minutes=10))
        self.assertEqual(r.nature_time_defer(), '提前 10 分钟')

    def test_reschedule(self):
        n = timezone.now() - timedelta(minutes=10)
        r = Remind(time=n, owner_id='miao', event='吃饭', desc='吃饭饭', repeat={REPEAT_KEY_DAY: 1}, defer=-60)
        r.save()
        self.assertEqual(r.notify_time, n - timedelta(minutes=60) + timedelta(days=1))

    def test_reschedule_monthly_edge_case(self):
        initial_time = datetime.datetime(2024, 1, 30, 10, 0, tzinfo=timezone.get_default_timezone())
        r = Remind(
            time=initial_time,
            owner_id='miao',
            event='月底提醒',
            repeat={REPEAT_KEY_MONTH: 1}
        )
        self.assertTrue(r.reschedule(initial_time))
        self.assertEqual(r.notify_time, datetime.datetime(2024, 2, 29, 10, 0, tzinfo=timezone.get_default_timezone()))
        # next reschedule should correct to 30
        self.assertTrue(r.reschedule(r.notify_time))
        self.assertEqual(r.notify_time, datetime.datetime(2024, 3, 30, 10, 0, tzinfo=timezone.get_default_timezone()))

    @mock.patch('remind.models.scheduler.close_old_connections')
    @mock.patch('remind.models.remind.notify_executor')
    def test_scheduler_skips_missed_repeat(self, executor, _):
        now = timezone.now()
        due = Remind(time=now - timedelta(minutes=1), owner_id='miao', desc='due')
        due.save()
        missed = Remind(time=now, owner_id='miao', desc='missed', repeat={REPEAT_KEY_DAY: 1})
        missed.save()
        # Simulate a downtime, bypassing the pre_save hook which reschedules on save
        missed_time = now - timedelta(hours=3)
        Remind.objects.filter(pk=missed.pk).update(time=missed_time, notify_time=missed_time)

        with self.captureOnCommitCallbacks(execute=True):
            RemindScheduler()._process_jobs()

        executor.submit.assert_called_once()  # only the due remind is sent
        due.refresh_from_db()
        missed.refresh_from_db()
        self.assertTrue(due.done)
        self.assertFalse(missed.done)
        self.assertEqual(missed.notify_time, missed_time + timedelta(days=1))
