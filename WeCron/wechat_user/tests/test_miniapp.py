# coding: utf-8
from unittest import mock

from django.test import TestCase, override_settings
from django.urls import reverse
from django.utils import timezone
from httmock import urlmatch, response, HTTMock
from rest_framework.authtoken.models import Token

from remind.models import Remind
from wechat_user.backends import make_guest
from wechat_user.miniapp import MiniAppLoginView
from wechat_user.models import WechatUser


def jscode2session_mock(unionid='the_unionid'):
    @urlmatch(netloc=r'(.*\.)?api\.weixin\.qq\.com$', path='/sns/jscode2session')
    def _mock(url, request):
        content = {'openid': 'mini_openid', 'session_key': 'SESSION_KEY', 'unionid': unionid}
        return response(200, content, {'Content-Type': 'application/json'}, request=request)
    return _mock


@override_settings(WX_MINIAPP_APPID='mini_appid', WX_MINIAPP_SECRET='mini_secret')
@mock.patch.object(MiniAppLoginView, 'throttle_classes', ())
class MiniAppLoginTestCase(TestCase):

    def setUp(self):
        self.user = WechatUser.objects.create(openid='mp_openid', nickname='miao', subscribe=True,
                                              unionid='the_unionid')

    def login(self, mock_handler=None):
        with HTTMock(mock_handler or jscode2session_mock()):
            return self.client.post(reverse('miniapp_login'), {'code': 'CODE'}, content_type='application/json')

    def test_login(self):
        resp = self.login()
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertEqual(data['token'], Token.objects.get(user=self.user).key)
        self.assertEqual(data['user']['id'], 'mp_openid')
        # Logging in again reuses the token
        self.assertEqual(self.login().json()['token'], data['token'])

    def test_not_subscribed(self):
        resp = self.login(jscode2session_mock(unionid='unknown'))
        self.assertEqual(resp.status_code, 403)
        self.assertEqual(resp.json()['code'], 'not_subscribed')

        self.user.subscribe = False
        self.user.save()
        resp = self.login()
        self.assertEqual(resp.status_code, 403)

    def test_token_access_api(self):
        Remind.objects.create(time=timezone.now() + timezone.timedelta(hours=1), owner=self.user, event='吃饭')
        auth = {'HTTP_AUTHORIZATION': 'Token ' + self.login().json()['token']}

        resp = self.client.get(reverse('remind-list'), **auth)
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(len(resp.json()['results']), 1)
        remind_id = resp.json()['results'][0]['id']

        # Writes need no CSRF token with token authentication
        resp = self.client.patch(reverse('remind-detail', args=(remind_id,)), {'title': '喝茶'},
                                 content_type='application/json', **auth)
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.json()['title'], '喝茶')

        resp = self.client.patch(reverse('profile-detail'), {'notify_subscription': False},
                                 content_type='application/json', **auth)
        self.assertEqual(resp.status_code, 200)
        self.assertFalse(resp.json()['notify_subscription'])

    def test_subscribe_keeps_existing_participants(self):
        other = WechatUser.objects.create(openid='other', nickname='other', subscribe=True)
        remind = Remind.objects.create(time=timezone.now() + timezone.timedelta(hours=1),
                                       owner=other, event='开会', participants=['someone_else'])
        auth = {'HTTP_AUTHORIZATION': 'Token ' + self.login().json()['token']}

        resp = self.client.post(reverse('remind-subscribe', args=(remind.pk.hex,)), **auth)
        self.assertEqual(resp.status_code, 200)
        remind.refresh_from_db()
        self.assertIn(self.user.pk, remind.participants)
        # The participant that was added concurrently by someone else is kept
        self.assertIn('someone_else', remind.participants)

        # Web guests who haven't subscribed the official account can't, and leave the remind untouched
        self.client.force_login(make_guest(pk='guest', nickname='guest'), backend='wechat_user.backends.WechatBackend')
        self.assertEqual(self.client.post(reverse('remind-subscribe', args=(remind.pk.hex,))).status_code, 403)
        remind.refresh_from_db()
        self.assertNotIn('guest', remind.participants)

    def test_new_time_resets_monthly_original_day(self):
        time = timezone.now() + timezone.timedelta(days=3)
        remind = Remind.objects.create(time=time, owner=self.user, event='还款',
                                       repeat={'month': 1, 'original_day': 31})
        auth = {'HTTP_AUTHORIZATION': 'Token ' + self.login().json()['token']}
        url = reverse('remind-detail', args=(remind.pk.hex,))

        # Unrelated edits keep it, though clients send the time back in whole seconds
        same_time = int(time.timestamp()) * 1000
        self.client.patch(url, {'desc': 'x', 'time': same_time}, content_type='application/json', **auth)
        remind.refresh_from_db()
        self.assertEqual(remind.repeat, {'month': 1, 'original_day': 31})

        new_time = int((time + timezone.timedelta(days=1)).timestamp()) * 1000
        resp = self.client.patch(url, {'time': new_time, 'repeat': {'month': 1, 'original_day': 31}},
                                 content_type='application/json', **auth)
        self.assertEqual(resp.status_code, 200)
        remind.refresh_from_db()
        self.assertEqual(remind.repeat, {'month': 1})

    def test_unsubscribed_token_rejected(self):
        auth = {'HTTP_AUTHORIZATION': 'Token ' + self.login().json()['token']}
        # Users with more than 100 reminds are kept
        Remind.objects.bulk_create([Remind(time=timezone.now(), owner=self.user) for _ in range(101)])
        self.user.unsubscribe()
        self.assertTrue(WechatUser.objects.filter(pk=self.user.pk).exists())
        self.assertEqual(self.client.get(reverse('remind-list'), **auth).status_code, 401)
