# coding: utf-8
from __future__ import unicode_literals, absolute_import
from datetime import timedelta

from django.test import TestCase
from django.utils import timezone
from remind.models import Remind
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
        self.assertEqual(r.notify_time, n-timedelta(minutes=10))
        self.assertEqual(r.nature_time_defer(), '提前 10 分钟')

    def test_reschedule(self):
        n = timezone.now() - timedelta(minutes=10)
        r = Remind(time=n, owner_id='miao', event='吃饭', desc='吃饭饭', repeat=(0, 0, 1, 0), defer=-60)
        r.save()
        self.assertEqual(r.notify_time,  n-timedelta(minutes=60)+timedelta(days=1))
