# coding: utf-8
from __future__ import unicode_literals, absolute_import
import logging
import uuid

from django.db import models
from django.db.models.signals import post_save
from common import wechat_client
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
    owner = models.ForeignKey('wxhook.User', verbose_name='创建者')

    class Meta:
        ordering = ["-time"]
        db_table = 'remind'

    def nature_time(self):
        return nature_time(self.time)

    def notify_users(self):
        wechat_client.message.send_template(
            user_id=self.owner.id,
            template_id='OHwCU_UbAW3XoaLJimwMzbc7RFQMCEX0OBZ4PvsDTuk',
            url=self.get_absolute_url(),
            top_color='#459ae9',
            data={
                   "first": {
                       "value": '\U0001f514%s\n' % self.event if self.event else
                           self.time.strftime('%Y/%m/%d %H:%M到了'),
                       "color": "#459ae9"
                   },
                   "keyword1": {
                       "value": self.time.strftime('%Y/%m/%d %H:%M'),
                   },
                   "keyword2": {
                       "value": self.desc
                   },
                   # "remark": {
                   #     "value": "欢迎再次购买！",
                   #     "color": "#459ae9"
                   # }
            },
        )

    def get_absolute_url(self):
        return 'http://www.weixin.at'


from django.dispatch import receiver

@receiver(post_save, sender='remind.Remind', dispatch_uid='update-scheduler')
def update_scheduler(sender, instance, **kwargs):
    scheduler.wakeup()
    scheduler.add_job(instance.notify_users,
                      next_run_time=instance.time,
                      id=str(instance.id),
                      replace_existing=True)

# post_save.connect(lambda *a, **k: scheduler.wakeup(),
#                   sender='remind.Remind',
#                   dispatch_uid='update-scheduler')
