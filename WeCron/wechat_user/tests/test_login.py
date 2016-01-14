# coding: utf-8
from __future__ import unicode_literals, absolute_import

from django.test import TestCase, LiveServerTestCase
from django.db.models.signals import post_save
from django.core.urlresolvers import reverse
from httmock import urlmatch, response, HTTMock
from wechat_user.models import WechatUser


class LoginTestCase(TestCase):
    def setUp(self):
        post_save.disconnect(dispatch_uid='update-scheduler')
        self.user = WechatUser(openid='fake_user', nickname='fake_user')
        self.user.save()
        # Disable scheduler

    def test_unlogged_in_user(self):
        resp = self.client.get(reverse('remind_list'))
        self.assertEqual(resp.status_code, 302)
        self.assertIn('open.weixin.qq.com/connect/oauth2/authorize', resp.url)
        resp = self.client.get(reverse('oauth_complete'))
        self.assertEqual(resp.status_code, 403)

    def test_log_in_existing_user(self):
        @urlmatch(netloc=r'(.*\.)?api\.weixin\.qq\.com$', path='/sns/oauth2/access_token')
        def web_access_token_mock(url, request):
            content = {
                   "access_token": "ACCESS_TOKEN",
                   "expires_in": 7200,
                   "refresh_token": "REFRESH_TOKEN",
                   "openid": "fake_user",
                   "scope": "SCOPE"
                }
            headers = {
                'Content-Type': 'application/json'
            }
            return response(200, content, headers, request=request)

        with HTTMock(web_access_token_mock):
            resp = self.client.get(reverse('oauth_complete'),
                                   data={'code': 123,
                                         'state': 'remind_list'})
            self.assertEqual(self.client.session['_auth_user_id'], self.user.pk)
            self.assertEqual(resp.status_code, 302)
            self.assertEqual(reverse('remind_list'), resp.url)

    def test_guest(self):
        guest_id = 'fake_user1xxx'
        @urlmatch(netloc=r'(.*\.)?api\.weixin\.qq\.com$', path='/sns/oauth2/access_token')
        def web_access_token_mock(url, request):
            content = {
                   "access_token": "ACCESS_TOKEN",
                   "expires_in": 7200,
                   "refresh_token": "REFRESH_TOKEN",
                   "openid": guest_id,
                   "scope": "SCOPE"
                }
            headers = {
                'Content-Type': 'application/json'
            }
            return response(200, content, headers, request=request)

        with HTTMock(web_access_token_mock):
            resp = self.client.get(reverse('oauth_complete'),
                                   data={'code': 123,
                                         'state': 'remind_list'})
            self.assertEqual(self.client.session['_auth_user_id'], guest_id)
            self.assertEqual(resp.status_code, 302)
            self.assertEqual(reverse('remind_list'), resp.url)
            self.assertFalse(WechatUser.objects.filter(pk=guest_id).exists())

