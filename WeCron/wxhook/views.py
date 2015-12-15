# coding: utf-8
from __future__ import unicode_literals, absolute_import
import logging

from wechat_sdk.exceptions import ParseError
from django.views.decorators.csrf import csrf_exempt
from django.http import HttpResponse
from django.views.generic import View

from .wechat_client import WechatClient

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

        self.wechat = WechatClient()

        if self.wechat.check_signature(signature=signature, timestamp=timestamp, nonce=nonce):
            return super(WeiXinHook, self).dispatch(request, *args, **kwargs)
        else:
            logger.warning('Illegal Access!')

        return HttpResponse('Welcome to WeCron')

    def get(self, request):
        return HttpResponse(request.GET.get('echostr', 'Welcome, you have successfully authorized!'))

    def post(self, request):
        try:
            wechat_resp = self.wechat.parse_message(request.body)
        except ParseError:
            logger.exception('Illegal message from weixin: \n%s', request.body)
            return HttpResponse('Illegal message from weixin: \n%s' % request.body)
        return HttpResponse(wechat_resp, content_type='text/xml; charset=utf-8')

