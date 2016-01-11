# coding: utf-8
from __future__ import unicode_literals, absolute_import
import logging
import uuid
from urlparse import urljoin

from django.db import models
from django.core.urlresolvers import reverse
from django.utils.timezone import localtime, now
from common import wechat_client
from remind.utils import nature_time

logger = logging.getLogger(__name__)


class Remind(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4)
    time = models.DateTimeField('提醒时间', db_index=True)
    create_time = models.DateTimeField('设置时间', default=now)
    desc = models.TextField('原始描述', default='', blank=True, null=True)
    event = models.TextField('提醒事件', default='', blank=True, null=True)
    media_url = models.URLField('语音', max_length=320, blank=True, null=True)
    repeat = models.CharField('重复', max_length=128, blank=True, null=True)
    owner = models.ForeignKey('wxhook.User', verbose_name='创建者',
                              related_name='time_reminds_created', on_delete=models.DO_NOTHING)
    participants = models.ManyToManyField('wxhook.User', verbose_name='订阅者',
                                         related_name='time_reminds_participate')
    status = models.CharField('状态', max_length=10, default='pending',
                              choices=(('pending', 'pending'),
                                       ('running', 'running'),
                                       ('done', 'done')))

    class Meta:
        ordering = ["-time"]
        db_table = 'time_remind'

    def nature_time(self):
        return nature_time(self.time)

    def local_time_string(self, fmt='%Y/%m/%d %H:%M'):
        return localtime(self.time).strftime(fmt)

    def title(self):
        if self.event:
            return self.event
        return '闹钟'

    def notify_users(self):
        logger.info('Sending notification to user %s', self.owner.nickname)
        wechat_client.message.send_template(
            user_id=self.owner_id,
            template_id='IxUSVxfmI85P3LJciVVcUZk24uK6zNvZXYkeJrCm_48',
            url=self.get_absolute_url(),
            top_color='#459ae9',
            data={
                   "first": {
                       "value": '\U0001F552 %s\n' % self.title(),
                       "color": "#459ae9"
                   },
                   "keyword1": {
                       "value": self.desc,
                   },
                   "keyword2": {
                       "value": self.local_time_string(),
                   },
            },
        )

    def get_absolute_url(self):
        return 'http://www.baidu.com'
        return urljoin('http://www.weixin.at', reverse('remind_detail', kwargs={'pk': self.pk.hex}))

    def __unicode__(self):
        return '%s: %s (%s)' % (self.owner.nickname, self.desc, self.local_time_string('%Y/%m/%d %H:%M:%S'))

