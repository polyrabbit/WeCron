# coding: utf-8
from __future__ import unicode_literals, absolute_import
import logging

from wechat_sdk import WechatBasic
from wechat_sdk.exceptions import ParseError
from django.conf import settings
from django.views.decorators.csrf import csrf_exempt
from django.http import HttpResponse
from django.views.generic import View

from .wechat_message_handler import handle

logger = logging.getLogger(__name__)


# import sys
# reload(sys)  # Reload does the trick!
# sys.setdefaultencoding('UTF8')


class WeiXinHook(View):

    @csrf_exempt
    def dispatch(self, request, *args, **kwargs):
        signature = request.GET.get('signature', '')
        timestamp = request.GET.get('timestamp', '')
        nonce = request.GET.get('nonce', '')

        self.wechat = WechatBasic(
                token=settings.WX_SIGN_TOKEN,
                appid=settings.WX_APPID,
                appsecret=settings.WX_APPSECRET
            )

        if self.wechat.check_signature(signature=signature, timestamp=timestamp, nonce=nonce):
            return super(WeiXinHook, self).dispatch(request, *args, **kwargs)

        return HttpResponse('Welcome to WeCron')

    def get(self, request):
        return HttpResponse(request.GET.get('echostr', 'Welcome, you have successfully authorized!'))

    def post(self, request):
        try:
            self.wechat.parse_data(request.body)
        except ParseError:
            logger.exception('Illegal message from weixin: \n%s', request.body)
            return HttpResponse('Illegal message from weixin: \n%s' % request.body)

        message = self.wechat.get_message()
        resp_txt = handle(message)
        return HttpResponse(self.wechat.response_text(resp_txt))

