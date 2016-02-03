# coding: utf-8
from __future__ import unicode_literals, absolute_import

from django.test import TestCase
from django.utils import timezone
from django.core.urlresolvers import reverse
from remind.models import Remind
from wechat_user.models import WechatUser


class RemindViewTestCase(TestCase):
    def setUp(self):
        self.r = Remind(time=timezone.now(), owner_id='miao', event='吃饭', desc='吃饭饭')
        self.r.save()

    def test_anonymous_delete(self):
        resp = self.client.get(reverse('remind_delete', args=(self.r.pk.hex,)))
        # self.assertEqual(resp.status_code, 302)
        self.assertIn('//open.weixin.qq.com/connect/oauth2/authorize', resp.url)

    def test_unauthorized_delete(self):
        u = WechatUser(openid='123', nickname='456')
        u.save()
        self.client.force_login(u)
        resp = self.client.get(reverse('remind_delete', args=(self.r.pk.hex,)))
        self.assertEqual(resp.status_code, 403)

    def test_participant_delete(self):
        self.r.add_participant('123')
        u = WechatUser(openid='123', nickname='456')
        u.save()
        self.client.force_login(u)
        resp = self.client.get(reverse('remind_delete', args=(self.r.pk.hex,)))
        self.assertEqual(resp.status_code, 302)
        self.assertEqual(resp.url, reverse('remind_list'))

    def test_delete(self):
        u = WechatUser(openid='miao', nickname='456')
        u.save()
        self.client.force_login(u)
        resp = self.client.get(reverse('remind_delete', args=(self.r.pk.hex,)))
        self.assertEqual(resp.status_code, 302)
        self.assertEqual(resp.url, reverse('remind_list'))
