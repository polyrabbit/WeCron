#coding: utf-8
from __future__ import unicode_literals, absolute_import
import logging

from common import wechat_client

logger = logging.getLogger(__name__)


# TODO, need to implement my own, wechat API is too slow and inaccurate.
def parse(text, **kwargs):
    return wechat_client.semantic.search(
        query=text,
        category='remind',
        city='上海', # F**k, weixin always needs the city param, hard-code one.
        **kwargs
    )
