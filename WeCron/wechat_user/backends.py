#coding: utf-8
import logging
from urllib.parse import quote_plus
from django.contrib.auth import get_user_model
from django.conf import settings
from django.urls import reverse
from rest_framework.authentication import TokenAuthentication
from requests import RequestException
from rest_framework.exceptions import AuthenticationFailed
from wechatpy import WeChatOAuthException, oauth

from common import wechat_client

logger = logging.getLogger(__name__)
UserModel = get_user_model()
# What WeChat tells instead of the real nickname when the user hasn't authorized
DEFAULT_NICKNAME = '微信用户'


class WeChatOAuth(oauth.WeChatOAuth):
    """wechatpy's OAuth client waits forever, use the same timeout as wechat_client"""

    def _request(self, method, url_or_endpoint, **kwargs):
        kwargs.setdefault('timeout', wechat_client.timeout)
        return super(WeChatOAuth, self)._request(method, url_or_endpoint, **kwargs)


def make_guest(**kw):
    u = UserModel(**kw)
    u.subscribe = False
    u.save = lambda **kw: 1
    return u


def authorize_url(request, state, scope='snsapi_userinfo'):
    """WeChat login URL. snsapi_userinfo asks for the nickname and avatar, which WeChat tells nowhere else"""
    return WeChatOAuth(
        app_id=settings.WX_APPID,
        secret=settings.WX_APPSECRET,
        redirect_uri=request.build_absolute_uri(reverse('oauth_complete')),
        scope=scope,
        # wechatpy doesn't encode it, and a "#" would cut the URL
        state=quote_plus(state),
    ).authorize_url


def update_profile(user, oauth_client):
    """Fills in the nickname and avatar, which WeChat only tells once the user grants snsapi_userinfo"""
    try:
        info = oauth_client.get_user_info()
    except (WeChatOAuthException, RequestException) as e:
        logger.warning('Failed to get user info of %s: %s', user.pk, e)
        return
    # Same rule as UserSerializer.validate_nickname, nicknames go into text messages that carry <a> links
    nickname = (info.get('nickname') or '').replace('<', '').replace('>', '').strip()
    if nickname == DEFAULT_NICKNAME:
        return  # Placeholders, e.g. on the snapshot pages opened from Moments
    headimgurl = info.get('headimgurl') or ''
    logger.debug('Got user info of %s: nickname=%r, headimgurl=%r', user.pk, nickname, headimgurl)
    fields = []
    # A nickname set by the user in the mini program wins
    if nickname and not user.nickname:
        user.nickname = nickname[:40]
        fields.append('nickname')
    if headimgurl and headimgurl != user.headimgurl:
        user.headimgurl = headimgurl
        fields.append('headimgurl')
    if fields:
        user.save(update_fields=fields)


class WechatBackend(object):

    def authenticate(self, request, code=None, redirect_uri=None, state=None):
        oauth_client = WeChatOAuth(
            app_id=settings.WX_APPID,
            secret=settings.WX_APPSECRET,
            redirect_uri=redirect_uri,
            scope='snsapi_base',
            state=state
        )

        try:
            res = oauth_client.fetch_access_token(code)
            user = UserModel.objects.get(pk=oauth_client.open_id)
        except (WeChatOAuthException, RequestException) as e:
            logger.warning('Failed to get access token due to %s', e)
            return None
        except UserModel.DoesNotExist:
            return make_guest(pk=oauth_client.open_id, nickname=oauth_client.open_id)
        # Users who declined snsapi_userinfo log in with snsapi_base, see OAuthComplete
        if 'snsapi_userinfo' in res.get('scope', ''):
            update_profile(user, oauth_client)
        return user

    def get_user(self, open_id):
        try:
            return UserModel.objects.get(pk=open_id)
        except UserModel.DoesNotExist:
            return make_guest(pk=open_id, nickname=open_id)


class SubscribedTokenAuthentication(TokenAuthentication):
    """Tokens stop working once their users unsubscribe the official account"""

    def authenticate_credentials(self, key):
        user, token = super(SubscribedTokenAuthentication, self).authenticate_credentials(key)
        if not user.subscribe:
            raise AuthenticationFailed('请先关注公众号')
        return user, token
