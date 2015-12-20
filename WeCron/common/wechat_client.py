#coding: utf-8
from __future__ import unicode_literals, absolute_import
import logging

from django.conf import settings
from wechatpy import WeChatClient

logger = logging.getLogger(__name__)

"""
A stateless client, there should be only one instance of wechat_client,
for there is only one instance of access_token globally.
"""
wechat_client = WeChatClient(
    appid=settings.WX_APPID,
    secret=settings.WX_APPSECRET
)

