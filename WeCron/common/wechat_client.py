#coding: utf-8
from __future__ import unicode_literals, absolute_import
import logging

from django.conf import settings
from wechatpy import WeChatClient
from shove import Shove
from wechatpy.session.shovestorage import ShoveStorage

logger = logging.getLogger(__name__)

shove = Shove('file:///tmp/wecron_storage', sync=1)
storage = ShoveStorage(shove)

"""
A stateless client, there should be only one instance of wechat_client,
for there is only one instance of access_token globally.
"""
wechat_client = WeChatClient(
    appid=settings.WX_APPID,
    secret=settings.WX_APPSECRET,
    session=storage
)
