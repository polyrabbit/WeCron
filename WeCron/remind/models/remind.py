# coding: utf-8
from __future__ import unicode_literals, absolute_import
import logging
import uuid
from urlparse import urljoin
from datetime import timedelta

from tomorrow import threads
from dateutil.relativedelta import relativedelta
from django.db import models
from django.core.urlresolvers import reverse
from django.conf import settings
from django.utils.timezone import localtime, now
from django.utils.formats import date_format
from django.contrib.postgres.fields import ArrayField
from django.db.models.signals import pre_save
from django.dispatch import receiver
from common import wechat_client
from remind.utils import nature_time

logger = logging.getLogger(__name__)


class Remind(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4)

    time = models.DateTimeField('时间', db_index=True)
    notify_time = models.DateTimeField('提醒时间', db_index=True, null=True)
    defer = models.IntegerField('提前提醒分钟', blank=True, default=0)

    create_time = models.DateTimeField('设置时间', default=now)
    desc = models.TextField('原始描述', default='', blank=True, null=True)
    remark = models.TextField('备注', default='', blank=True, null=True)
    event = models.TextField('提醒事件', default='', blank=True, null=True)
    media_id = models.URLField('语音消息媒体id', max_length=120, blank=True, null=True)
    # year, month, day, week, hour, minute
    repeat = ArrayField(models.IntegerField(), size=4, verbose_name='重复', default=list)
    owner = models.ForeignKey(settings.AUTH_USER_MODEL, verbose_name='创建者',
                              related_name='time_reminds_created', on_delete=models.DO_NOTHING)
    # participants = models.ManyToManyField('wechat_user.WechatUser', verbose_name='订阅者',
    #                                       related_name='time_reminds_participate')
    participants = ArrayField(models.CharField(max_length=40), verbose_name='订阅者', default=list)
    done = models.NullBooleanField('状态', default=False,
                                   choices=((False, '未发送'), (True, '已发送'),))

    default_title = u'闹钟'

    class Meta:
        ordering = ["-time"]
        db_table = 'time_remind'

    def time_until(self):
        """Returns 11小时28分后"""
        return nature_time(self.time)

    def nature_time_defer(self):
        if not self.defer:
            return '准时'
        units = [('周', 10080), ('天', 1440), ('小时', 60), ('分钟', 1)]
        for unit, minutes in units:
            if self.defer % minutes == 0:
                return '%s %s %s' %('提前' if self.defer < 0 else '延后',
                                    abs(self.defer/minutes), unit)

    def local_time_string(self, fmt=None):
        """
        Take format from django
        https://docs.djangoproject.com/en/dev/ref/templates/builtins/#date
        """
        dt = localtime(self.time)
        if not fmt:
            fmt = 'Y/n/j(D) G:i'  # '2016/11/21(周一) 12:20'
            if dt.year == localtime(now()).year:
                fmt = u'n月j日(D) G:i'  # '11月21日(周一) 12:20'
        return date_format(dt, format=fmt, use_l10n=True)

    def title(self):
        if self.event:
            return self.event
        return self.default_title

    # TODO: not suitable using async here, for reschedule may already have modified self.time
    # @threads(10, timeout=60)
    def notify_user_by_id(self, uid):
        # TODO: wechatpy is not thread-safe
        try:
            user = self.owner._default_manager.get(pk=uid)
        except self.owner.DoesNotExist:
            logger.info('User %s is not found, skip sending notification' % uid)
            return
        name = user.get_full_name()
        if not user.subscribe:
            logger.info('User %s has unsubscribed, skip sending notification' % name)
            return
        try:
            res = wechat_client.message.send_template(
                        user_id=uid,
                        template_id='IxUSVxfmI85P3LJciVVcUZk24uK6zNvZXYkeJrCm_48',
                        url=self.get_absolute_url(full=True),
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
                                   "value": self.local_time_string('Y/n/d(D) G:i'),
                               },
                               "remark": {
                                   "value": "提醒时间：" + self.nature_time_defer()
                                            + ('\n重复周期：' + self.get_repeat_text()) if self.has_repeat() else '',
                               }
                        },
                    )
            logger.info('Successfully send notification(%s) to user %s', self.desc, name)
            return res
        except:
            logger.exception('Failed to send notification(%s) to user %s', self.desc, name)

    def notify_users(self):
        for uid in [self.owner_id] + self.participants:
            self.notify_user_by_id(uid)

    def add_participant(self, uid):
        if uid == self.owner_id or uid in self.participants:
            return False
        self.participants.append(uid)
        self.save(update_fields=['participants'])
        return True

    def remove_participant(self, uid):
        if uid not in self.participants:
            return
        self.participants.remove(uid)
        self.save(update_fields=['participants'])

    def has_repeat(self):
        return self.repeat and len(self.repeat) >= 4 and self.repeat != [0]*len(self.repeat)

    def get_repeat_text(self):
        if self.has_repeat():
            # TODO: we don't support hour and minute now
            repeat_names = ('年', '月', '天', '周', '小时', '分钟')
            for idx, repeat_count in enumerate(self.repeat):
                if repeat_count:
                    return '每%s%s' % (
                        '' if repeat_count == 1 else repeat_count, repeat_names[idx])
        return

    def reschedule(self):
        if not self.has_repeat():
            return False
        _now = now()
        self.update_notify_time()
        if _now < self.notify_time:
            return False
        delta_keys = ['years', 'months', 'days', 'weeks', 'hours', 'minutes']
        delta = {}
        for idx, repeat_count in enumerate(self.repeat):
            delta[delta_keys[idx]] = repeat_count
        while self.notify_time <= _now:
            self.time += relativedelta(**delta)
            self.update_notify_time()
        return True

    def update_notify_time(self):
        self.notify_time = self.time + timedelta(minutes=self.defer)

    def subscribed_by(self, user):
        return self.owner_id == user.pk or user.pk in self.participants

    def get_absolute_url(self, full=False):
        # url = reverse('remind-detail', kwargs={'pk': self.pk.hex})
        url = '/reminds/#/' + self.pk.hex
        if full:
            return urljoin('http://wecron.betacat.io', url)
        return url

    def get_api_endpoint(self):
        return reverse('remind-detail', kwargs={'pk': self.pk.hex})

    def __unicode__(self):
        return '%s: %s (%s)' % (self.owner.nickname, self.desc or self.event,
                                self.local_time_string('Y/n/j G:i:s'))


@receiver(pre_save, sender=Remind, dispatch_uid='update-notify-time')
def update_notify_time(instance, **kwargs):
    if instance.reschedule():
        instance.done = False
    instance.update_notify_time()
