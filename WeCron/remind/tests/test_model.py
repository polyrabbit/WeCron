# coding: utf-8
from __future__ import unicode_literals, absolute_import

import datetime
from datetime import timedelta

from django.test import TestCase
from django.utils import timezone
from remind.models import Remind
from remind.models.remind import REPEAT_KEY_DAY, REPEAT_KEY_MONTH
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
