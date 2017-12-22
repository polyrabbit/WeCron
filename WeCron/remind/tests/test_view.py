# coding: utf-8
from __future__ import unicode_literals, absolute_import

from django.test import TestCase
from django.utils import timezone
from django.core.urlresolvers import reverse
from remind.models import Remind
from wechat_user.models import WechatUser


class RemindViewTestCase(TestCase):
    def setUp(self):
        self.user = WechatUser(openid='miao', nickname='456')
        self.user.save()
        self.r = Remind(time=timezone.now(), owner_id='miao', event='吃饭', desc='吃饭饭')
        self.r.save()

    def test_anonymous_delete(self):
        resp = self.client.delete(reverse('remind-detail', args=(self.r.pk.hex,)), HTTP_X_REFERER='abc.com/#def')
        # self.assertEqual(resp.status_code, 302)
        self.assertEqual(resp.status_code, 401)
        self.assertIn('//open.weixin.qq.com/connect/oauth2/authorize', resp.get('WWW-Authenticate', ''))
        self.assertIn('state=abc.com%2F%23def', resp.get('WWW-Authenticate', ''))

    def test_unauthorized_delete(self):
        u = WechatUser(openid='123', nickname='456')
        u.save()
        self.client.force_login(u)
        resp = self.client.delete(reverse('remind-detail', args=(self.r.pk.hex,)))
        self.assertEqual(resp.status_code, 403)

    def test_participant_delete(self):
        u = WechatUser(openid='123', nickname='456')
        u.save()
        self.r.add_participant('123')
        self.client.force_login(u)
        resp = self.client.delete(reverse('remind-detail', args=(self.r.pk.hex,)))
        self.assertEqual(resp.status_code, 204)
        # self.assertEqual(resp.url, reverse('remind_list'))

    def test_delete(self):
        self.client.force_login(self.user)
        resp = self.client.delete(reverse('remind-detail', args=(self.r.pk.hex,)))
        self.assertEqual(resp.status_code, 204)
        # self.assertEqual(resp.url, reverse('remind_list'))
