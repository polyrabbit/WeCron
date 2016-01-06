#coding: utf-8
from __future__ import unicode_literals, absolute_import
import logging
import json

from django.utils.dateparse import parse_datetime
from django.utils import timezone
from common import wechat_client
from remind.models import Remind

logger = logging.getLogger(__name__)


# TODO, need to implement my own, wechat API is unstable and inaccurate.
def parse(text, **kwargs):
    """Returns a Remind"""
    return parse_by_wechat_api(text, **kwargs)


def parse_by_wechat_api(text, **kwargs):
    """
    {
        "errcode": 0,
        "query": "提醒我上午十点开会",
        "semantic": {
            "details": {
                "answer": "",
                "context_info": {},
                "datetime": {
                    "date": "2015-12-23",
                    "date_lunar": "2015-11-13",
                    "time": "10:00:00",
                    "time_ori": "上午十点",
                    "type": "DT_ORI",
                    "week": "3"
                },
                "event": "开会",
                "hit_str": "提醒 我 上午 十点 开会 ",
                "remind_type": "0"
            },
            "intent": "SEARCH"
        },
        "type": "remind"
    }
    """
    wechat_result = wechat_client.semantic.search(
        query=text,
        category='remind',
        city='上海', # F**k, weixin always needs the city param, hard-code one.
        **kwargs
    )
    # wechat_result = json.loads(parse_by_wechat_api.__doc__)
    logger.info('Semantic result from wechat, %s', json.dumps(
        wechat_result, ensure_ascii=False, indent=2))

    dt_str = '%s %s+08:00' % (
        wechat_result['semantic']['details']['datetime']['date'],
        wechat_result['semantic']['details']['datetime']['time'],
    )  # there could be nothing in details
    dt = parse_datetime(dt_str)
    if dt <= timezone.now():  # GMT and UTC time can compares
        # TODO use a specified exception
        raise ValueError('/:no%s已经过去了，请重设一个将来的提醒。' % dt.strftime('%Y-%m-%d %H:%M:%S'))
    return Remind(time=dt,
                  desc=wechat_result.get('query', ''),
                  event=wechat_result['semantic']['details'].get('event', ''))
