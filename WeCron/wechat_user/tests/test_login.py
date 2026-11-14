# coding: utf-8

from django.test import TestCase, LiveServerTestCase
from django.db.models.signals import post_save
from django.urls import reverse
import requests
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
            self.user.refresh_from_db()
            self.assertIsNone(self.user.last_message_time)  # web logins don't open WeChat's messaging window

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



def oauth_userinfo_mock(nickname='awk', headimgurl='https://thirdwx.qlogo.cn/mmopen/abc/132'):
    calls = []

    @urlmatch(netloc=r'(.*\.)?api\.weixin\.qq\.com$', path='/sns/userinfo')
    def _userinfo_mock(url, request):
        calls.append(url)
        content = {'openid': 'fake_user', 'nickname': nickname, 'headimgurl': headimgurl}
        return response(200, content, {'Content-Type': 'application/json'}, request=request)
    _userinfo_mock.calls = calls
    return _userinfo_mock


class UserInfoLoginTestCase(TestCase):

    def setUp(self):
        self.user = WechatUser.objects.create(openid='fake_user', subscribe=True)

    def complete(self, scope, userinfo):
        with HTTMock(oauth_access_token_mock(scope=scope), userinfo):
            return self.client.get(reverse('oauth_complete'), data={'code': 'CODE', 'state': '/reminds/'})

    def test_login_asks_for_userinfo(self):
        resp = self.client.get(reverse('remind-list'), HTTP_X_REFERER='/reminds/#/settings')
        self.assertEqual(resp.status_code, 401)
        login_url = resp['WWW-Authenticate']
        self.assertIn('scope=snsapi_userinfo', login_url)
        self.assertIn('state=%2Freminds%2F%23%2Fsettings', login_url)

    def test_declined_falls_back_to_silent_login(self):
        # WeChat comes back without a code when the user declines
        resp = self.client.get(reverse('oauth_complete'), data={'state': '/reminds/'})
        self.assertEqual(resp.status_code, 302)
        self.assertIn('scope=snsapi_base', resp.url)
        self.assertIn('state=%2Freminds%2F', resp.url)

    def test_fills_nickname_and_avatar(self):
        resp = self.complete('snsapi_userinfo', oauth_userinfo_mock())
        self.assertEqual(resp.status_code, 302)
        self.assertEqual(resp.url, '/reminds/')
        self.user.refresh_from_db()
        self.assertEqual(self.user.nickname, 'awk')
        self.assertEqual(self.user.headimgurl, 'https://thirdwx.qlogo.cn/mmopen/abc/132')

    def test_keeps_nickname_set_by_user(self):
        self.user.nickname = '小明'
        self.user.save()
        self.complete('snsapi_userinfo', oauth_userinfo_mock())
        self.user.refresh_from_db()
        self.assertEqual(self.user.nickname, '小明')
        self.assertEqual(self.user.headimgurl, 'https://thirdwx.qlogo.cn/mmopen/abc/132')

    def test_nickname_without_angle_brackets(self):
        self.complete('snsapi_userinfo', oauth_userinfo_mock(nickname='<a href="x">awk</a>'))
        self.user.refresh_from_db()
        self.assertEqual(self.user.nickname, 'a href="x"awk/a')

    def test_blank_userinfo_changes_nothing(self):
        self.complete('snsapi_userinfo', oauth_userinfo_mock(nickname='', headimgurl=''))
        self.user.refresh_from_db()
        self.assertFalse(self.user.nickname)
        self.assertFalse(self.user.headimgurl)

    def test_default_nickname_ignored(self):
        self.complete('snsapi_userinfo', oauth_userinfo_mock(nickname='微信用户'))
        self.user.refresh_from_db()
        self.assertFalse(self.user.nickname)
        self.assertFalse(self.user.headimgurl)

    def test_userinfo_failure_still_logs_in(self):
        @urlmatch(netloc=r'(.*\.)?api\.weixin\.qq\.com$', path='/sns/userinfo')
        def broken(url, request):
            raise requests.ConnectionError('timed out')
        resp = self.complete('snsapi_userinfo', broken)
        self.assertEqual(resp.status_code, 302)
        self.assertEqual(self.client.session['_auth_user_id'], self.user.pk)

    def test_redirects_only_within_site(self):
        with HTTMock(oauth_access_token_mock()):
            resp = self.client.get(reverse('oauth_complete'), data={'code': 'CODE', 'state': 'https://evil.example/'})
        self.assertEqual(resp.url, '/')

    def test_silent_login_skips_userinfo(self):
        userinfo = oauth_userinfo_mock()
        self.complete('snsapi_base', userinfo)
        self.assertEqual(userinfo.calls, [])
        self.user.refresh_from_db()
        self.assertFalse(self.user.nickname)
