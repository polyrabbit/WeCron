# coding: utf-8

from django.test import TestCase, LiveServerTestCase
from django.db.models.signals import post_save
from django.urls import reverse
from httmock import urlmatch, response, HTTMock
from wechat_user.models import WechatUser


def oauth_access_token_mock(openid='fake_user', scope='snsapi_base'):
    @urlmatch(netloc=r'(.*\.)?api\.weixin\.qq\.com$', path='/sns/oauth2/access_token')
    def _access_token_mock(url, request):
        content = {
            'access_token': 'ACCESS_TOKEN',
            'expires_in': 7200,
            'refresh_token': 'REFRESH_TOKEN',
            'openid': openid,
            'scope': scope
        }
        headers = {
            'Content-Type': 'application/json'
        }
        return response(200, content, headers, request=request)
    return _access_token_mock


class LoginTestCase(TestCase):
    def setUp(self):
        post_save.disconnect(dispatch_uid='update-scheduler')
        self.user = WechatUser(openid='fake_user', nickname='fake_user')
        self.user.save()
        # Disable scheduler

    def test_unlogged_in_user(self):
        resp = self.client.get(reverse('remind-list'))
        self.assertEqual(resp.status_code, 401)
        self.assertIn('//open.weixin.qq.com/connect/oauth2/authorize', resp.get('WWW-Authenticate', ''))
        # Without a code (declined) it logs in silently instead
        resp = self.client.get(reverse('oauth_complete'))
        self.assertEqual(resp.status_code, 302)
        self.assertIn('scope=snsapi_base', resp.url)

    def test_log_in_existing_user(self):

        with HTTMock(oauth_access_token_mock()):
            resp = self.client.get(reverse('oauth_complete'),
                                   data={'code': 123,
                                         'state': 'remind-list-blah'})
            self.assertEqual(self.client.session['_auth_user_id'], self.user.pk)
            self.assertEqual(resp.status_code, 302)
            self.assertEqual('remind-list-blah', resp.url)

    def test_guest(self):
        guest_id = 'fake_user1xxx'
        with HTTMock(oauth_access_token_mock(guest_id)):
            resp = self.client.get(reverse('oauth_complete'),
                                   data={'code': 123,
                                         'state': 'remind-list-blah'})
            self.assertEqual(self.client.session['_auth_user_id'], guest_id)
            self.assertEqual(resp.status_code, 302)
            self.assertEqual('remind-list-blah', resp.url)
            self.assertFalse(WechatUser.objects.filter(pk=guest_id).exists())


@urlmatch(netloc=r'(.*\.)?api\.weixin\.qq\.com$', path='/sns/userinfo')
def oauth_userinfo_mock(url, request):
    content = {'openid': 'fake_user', 'nickname': 'awk', 'headimgurl': 'https://thirdwx.qlogo.cn/mmopen/abc/132'}
    return response(200, content, {'Content-Type': 'application/json'}, request=request)


class UserInfoLoginTestCase(TestCase):

    def setUp(self):
        self.user = WechatUser.objects.create(openid='fake_user', subscribe=True)

    def complete(self):
        with HTTMock(oauth_access_token_mock(scope='snsapi_userinfo'), oauth_userinfo_mock):
            return self.client.get(reverse('oauth_complete'), data={'code': 'CODE', 'state': '/reminds/'})

    def test_fills_nickname_and_avatar(self):
        resp = self.complete()
        self.assertEqual(resp.status_code, 302)
        self.assertEqual(resp.url, '/reminds/')
        self.user.refresh_from_db()
        self.assertEqual(self.user.nickname, 'awk')
        self.assertEqual(self.user.headimgurl, 'https://thirdwx.qlogo.cn/mmopen/abc/132')

    def test_keeps_nickname_set_by_user(self):
        self.user.nickname = '小明'
        self.user.save()
        self.complete()
        self.user.refresh_from_db()
        self.assertEqual(self.user.nickname, '小明')
        self.assertEqual(self.user.headimgurl, 'https://thirdwx.qlogo.cn/mmopen/abc/132')
