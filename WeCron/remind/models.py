# coding: utf-8
from __future__ import unicode_literals, absolute_import
import logging
import uuid

from django.db import models
from django.db.models.signals import post_save
from django.utils.dateparse import parse_datetime
from django.utils import timezone
from .scheduler import scheduler
from .utils import nature_time

logger = logging.getLogger(__name__)


class Remind(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4)
    time = models.DateTimeField('提醒时间')
    desc = models.TextField('原始描述', default='', blank=True, null=True)
    event = models.TextField('提醒事件', default='', blank=True, null=True)
    media_url = models.URLField('语音', max_length=320, blank=True, null=True)
    repeat = models.CharField('重复', max_length=128, blank=True, null=True)

    class Meta:
        ordering = ["-time"]
        db_table = 'remind'

    def nature_time(self):
        return nature_time(self.time)

    @classmethod
    def from_wechat_api(cls, resp_json):
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
        dt_str = '%s %s+08:00' % (
            resp_json['semantic']['details']['datetime']['date'],
            resp_json['semantic']['details']['datetime']['time'],
        )  # there could be nothing in details
        dt = parse_datetime(dt_str)
        if dt <= timezone.now():  # GMT and UTC time can compares
            # TODO use a specified exception
            raise ValueError('/:no时间已过，请改后再试。')

        remind = cls(time=dt,
                     desc=resp_json.get('query', ''),
                     event=resp_json['semantic']['details'].get('event', ''))
        remind.save()
        return remind


post_save.connect(lambda *a, **k: scheduler.wakeup(),
                  sender='remind.Remind',
                  dispatch_uid='update-scheduler')
