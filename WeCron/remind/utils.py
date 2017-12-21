# coding: utf-8
from __future__ import unicode_literals, absolute_import
from datetime import timedelta

from django.utils import timezone, lru_cache
from common import wechat_client


def delta2dict( delta ):
    """Accepts a delta, returns a dictionary of units"""
    delta = abs( delta )
    return {
        '年': int(delta.days / 365),
        '天': int(delta.days % 365),
        '小时': int(delta.seconds / 3600),
        '分钟': int(delta.seconds / 60) % 60,
        '秒': delta.seconds % 60,
        '毫秒': delta.microseconds
    }


def nature_time(dt, precision=2, past_tense='{}前', future_tense='{}后'):
    """Accept a datetime or timedelta, return a human readable delta string,
    Steal from ago.human
    """
    now = timezone.now().replace(microsecond=0)
    delta = dt
    if type(dt) is not type(timedelta()):
        delta = dt - now

    the_tense = future_tense
    if delta < timedelta(0):
        the_tense = past_tense

    d = delta2dict(delta)
    hlist = []
    count = 0
    units = ('年', '天', '小时', '分钟', '秒', '毫秒')
    for unit in units:
        if count >= precision:
            break  # met precision
        if d[unit] == 0:
            continue  # skip 0's
        if hlist and unit == units[-1]:  # skip X秒XX毫秒
            break
        hlist.append('%s%s' % (d[unit], unit))
        count += 1
    human_delta = ''.join(hlist)
    return the_tense.format(human_delta)


def get_qrcode_url(scene_id):
    ticket = wechat_client.qrcode.create({
        'expire_seconds': 2592000,
        'action_name': 'QR_LIMIT_STR_SCENE',
        'action_info': {
            'scene': {'scene_str': scene_id},
        }
    })
    return wechat_client.qrcode.get_url(ticket)