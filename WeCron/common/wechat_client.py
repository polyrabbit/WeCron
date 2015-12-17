#coding: utf-8
from __future__ import unicode_literals, absolute_import
import logging

from django.conf import settings
from wechat_sdk import WechatBasic

logger = logging.getLogger(__name__)


class WechatClient(WechatBasic):
    """A stateless class"""

    def __new__(cls, *args, **kw):
        if not hasattr(cls, '_instance'):
            cls._instance = super(WechatClient, cls).__new__(cls, *args, **kw)
        return cls._instance

    def __init__(self):
        super(WechatClient, self).__init__(
                appid=settings.WX_APPID,
                appsecret=settings.WX_APPSECRET
            )

wechat_client = WechatClient()
