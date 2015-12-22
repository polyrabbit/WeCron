#coding: utf-8
from __future__ import unicode_literals, absolute_import
import logging
import uuid

from django.db import models
from django.utils import timezone

logger = logging.getLogger(__name__)


class Remind(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4)
    next_run = models.DateTimeField('提醒时间')
    event = models.TextField('提醒事件', blank=True, null=True)
    media_url = models.URLField('语音', max_length=320, blank=True, null=True)
    repeat = models.CharField('重复', max_length=128, blank=True, null=True)

    @classmethod
    def from_wechat_api(cls, resp_json):
        now = timezone.now()
        resp_json['semantic']['details']['datetime']['date']

        event = resp_json.get('')