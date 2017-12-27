# coding: utf-8
from __future__ import unicode_literals, absolute_import

from django.test import TestCase
from django.utils import timezone
from httmock import urlmatch, response, with_httmock
from common.tests import access_token_mock
from .test_serializers import create_qrcode_mock
from remind.models import Remind
from wechat_user.models import WechatUser
from remind.share_post import draw_post, TPL_IMAGE_PATH


DISPLAY_POST = True


@urlmatch(netloc=r'(.*\.)?mp\.weixin\.qq\.com$', path='.*showqrcode')
def get_qr_image_mock(url, request):
    content = open(TPL_IMAGE_PATH, 'rb').read()
    headers = {
        'Content-Type': 'image/png'
    }
    return response(200, content, request=request)


class SharePostTestCase(TestCase):

    def setUp(self):
        self.user = WechatUser(openid='miao', nickname='miaomiao', subscribe=True, last_login=timezone.now())
        self.user.save()

    @with_httmock(access_token_mock, create_qrcode_mock, get_qr_image_mock)
    def test_one_line_description(self):
        r = Remind(time=timezone.now(), owner_id='miao', event='吃饭', desc='吃饭饭')
        image = draw_post(r, self.user)

        if DISPLAY_POST:
            image.show()

    @with_httmock(access_token_mock, create_qrcode_mock, get_qr_image_mock)
    def test_two_lines_description(self):
        r = Remind(time=timezone.now(), owner_id='miao', event='吃饭', desc='吃饭饭'*5)
        image = draw_post(r, self.user)

        if DISPLAY_POST:
            image.show()

    @with_httmock(access_token_mock, create_qrcode_mock, get_qr_image_mock)
    def test_many_lines_description(self):
        r = Remind(time=timezone.now(), owner_id='miao', event='吃饭', desc='吃饭饭' * 50)
        image = draw_post(r, self.user)

        if DISPLAY_POST:
            image.show()

    @with_httmock(access_token_mock, create_qrcode_mock, get_qr_image_mock)
    def test_lines_with_carriage(self):
        desc = """2018 NEO编程日 第1站  时间：2018年1月13日13：00（签到）—18：30（下午）""" + \
            """\n地点：上海浦东新区金科路长泰广场C座12层
                    """
        r = Remind(time=timezone.now(), owner_id='miao', event='吃饭', desc=desc)
        image = draw_post(r, self.user)

        if DISPLAY_POST:
            image.show()


