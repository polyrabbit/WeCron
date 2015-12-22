#coding: utf-8
from __future__ import unicode_literals, absolute_import
import logging
import json

from common import wechat_client
from remind.models import Remind

logger = logging.getLogger(__name__)


# TODO, need to implement my own, wechat API is unstable and inaccurate.
def parse(text, **kwargs):

    # wechat_result = json.loads(Remind.from_wechat_api.__doc__)
    wechat_result = wechat_client.semantic.search(
        query=text,
        category='remind',
        city='上海', # F**k, weixin always needs the city param, hard-code one.
        **kwargs
    )
    logger.info('Semantic result from wechat, %s', json.dumps(wechat_result, ensure_ascii=False, indent=2))
    return Remind.from_wechat_api(wechat_result)
