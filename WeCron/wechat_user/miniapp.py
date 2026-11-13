# coding: utf-8
"""Login for the WeChat mini program, users are matched with the official account by UnionID."""
import logging

import requests
from django.conf import settings
from django.contrib.auth import get_user_model
from rest_framework import permissions, status
from rest_framework.authtoken.models import Token
from rest_framework.response import Response
from rest_framework.views import APIView

from wechat_user.serializers import UserSerializer

logger = logging.getLogger(__name__)
UserModel = get_user_model()

JSCODE2SESSION_URL = 'https://api.weixin.qq.com/sns/jscode2session'
NOT_CONFIGURED = {'code': 'not_configured', 'detail': '小程序登录尚未配置'}


class MiniAppLoginError(Exception):
    pass


def code_to_session(code):
    """Returns a dict containing ``openid``, ``session_key`` and ``unionid``"""
    try:
        resp = requests.get(JSCODE2SESSION_URL, params={
            'appid': settings.WX_MINIAPP_APPID,
            'secret': settings.WX_MINIAPP_SECRET,
            'js_code': code,
            'grant_type': 'authorization_code',
        }, timeout=10)
        data = resp.json()
    except requests.RequestException as e:
        # The exception text holds the full URL, which contains the app secret, so only the type is kept
        raise MiniAppLoginError('Failed to request code2session: %s' % type(e).__name__)
    except ValueError:
        raise MiniAppLoginError('Malformed response from code2session')
    if data.get('errcode') or not data.get('openid'):
        raise MiniAppLoginError('code2session error %s: %s' % (data.get('errcode'), data.get('errmsg')))
    return data


class MiniAppLoginView(APIView):
    authentication_classes = ()
    permission_classes = (permissions.AllowAny,)
    throttle_scope = 'miniapp.login'

    def post(self, request):
        code = request.data.get('code') if isinstance(request.data, dict) else None
        if not code:
            return Response({'code': 'invalid_code', 'detail': '缺少登录凭证 code'},
                            status=status.HTTP_400_BAD_REQUEST)

        if not settings.WX_MINIAPP_SECRET:
            logger.error('Mini program login is not configured, set WX_MINIAPP_APPID and WX_MINIAPP_SECRET')
            return Response(NOT_CONFIGURED, status=status.HTTP_503_SERVICE_UNAVAILABLE)
        try:
            session = code_to_session(code)
        except MiniAppLoginError as e:
            logger.warning('Mini program login failed: %s', e)
            return Response({'code': 'invalid_code', 'detail': '微信登录失败，请稍后再试'},
                            status=status.HTTP_401_UNAUTHORIZED)
        unionid = session.get('unionid')
        if not unionid:
            logger.error('No UnionID from code2session, bind the mini program to the Open Platform account')
            return Response(NOT_CONFIGURED, status=status.HTTP_503_SERVICE_UNAVAILABLE)
        user = UserModel.objects.filter(unionid=unionid, subscribe=True).first()
        if user is None:
            logger.info('Mini program user(unionid=%s) has not subscribed the official account', unionid)
            return Response({'code': 'not_subscribed', 'detail': '请先关注公众号「微定时」'},
                            status=status.HTTP_403_FORBIDDEN)

        token, _ = Token.objects.get_or_create(user=user)
        logger.info('User %s logged into the mini program', user.get_full_name())
        return Response({'token': token.key, 'user': UserSerializer(user).data})
