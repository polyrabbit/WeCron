# coding: utf-8
from __future__ import unicode_literals, absolute_import
import logging

from django.conf import settings
from django.views.decorators.csrf import csrf_exempt
from django.http import HttpResponse
from django.views.generic import View

from wechatpy.utils import check_signature
from wechatpy import parse_message
from wechatpy.exceptions import InvalidSignatureException

from .message_handler import handle_message

logger = logging.getLogger(__name__)


class WeiXinHook(View):

    @csrf_exempt
    def dispatch(self, request, *args, **kwargs):
        signature = request.GET.get('signature', '')
        timestamp = request.GET.get('timestamp', '')
        nonce = request.GET.get('nonce', '')

        try:
            check_signature(settings.WX_SIGN_TOKEN, signature, timestamp, nonce)
            return super(WeiXinHook, self).dispatch(request, *args, **kwargs)
        except InvalidSignatureException:
            logger.warning('Invalid signature when accessing %s', request.get_full_path())
            return HttpResponse('Welcome to WeCron')

    def get(self, request):
        return HttpResponse(request.GET.get('echostr', 'Welcome, you have successfully authorized!'))

    def post(self, request):
        try:
            req_text = request.body.decode('utf-8')
            msg = parse_message(req_text)
        except Exception as e:
            logger.exception('Illegal message from weixin: \n%s', req_text)
            return HttpResponse('Illegal message from weixin: \n%s' % req_text)
        wechat_resp = handle_message(msg)
        return HttpResponse(wechat_resp, content_type='text/xml; charset=utf-8')

