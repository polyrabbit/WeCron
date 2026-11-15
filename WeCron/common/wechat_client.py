#coding: utf-8
import logging
from functools import partial

from django.conf import settings
from django.core.cache import caches
from wechatpy import WeChatClient

logger = logging.getLogger(__name__)

"""
A stateless client, there should be only one instance of wechat_client,
for there is only one instance of access_token globally.
"""
wechat_client = WeChatClient(
    appid=settings.WX_APPID,
    secret=settings.WX_APPSECRET,
    session=caches['wechat'],
    # Replies to WeChat's callbacks must be sent within 5 seconds, and requests waits forever by default
    timeout=4,
)
# wechatpy fetches access tokens without passing the timeout, so make it the session's default
wechat_client._http.request = partial(wechat_client._http.request, timeout=wechat_client.timeout)
