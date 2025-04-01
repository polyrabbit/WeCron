# coding: utf-8
from __future__ import unicode_literals, absolute_import
import logging
import uuid
from urlparse import urljoin

from tomorrow import threads
from dateutil.relativedelta import relativedelta
from django.db import models
from django.core.urlresolvers import reverse
from django.conf import settings
from django.utils.timezone import localtime, now, timedelta
from django.utils.formats import date_format
from django.contrib.postgres.fields import ArrayField, JSONField
from django.db.models.signals import pre_save
from django.dispatch import receiver
from common import wechat_client
from remind.utils import nature_time
from remind.signals import participant_modified
from wechatpy import WeChatException

logger = logging.getLogger(__name__)

REPEAT_KEY_YEAR     = 'year'
REPEAT_KEY_MONTH    = 'month'
REPEAT_KEY_DAY      = 'day'
REPEAT_KEY_WEEK     = 'week'
REPEAT_KEY_HOUR     = 'hour'
REPEAT_KEY_MINUTE   = 'minute'


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
    external_url = models.URLField('外部链接地址', max_length=120, blank=True, null=True)
    # year, month, day, week, hour, minute
    # repeat = ArrayField(models.IntegerField(), size=5, verbose_name='重复', default=list)
    repeat = JSONField(verbose_name='重复', default=dict)
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
                return '%s %s %s' % ('提前' if self.defer < 0 else '延后',
                                     abs(self.defer / minutes), unit)

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

    def notify_users(self):
        for uid in frozenset([self.owner_id] + self.participants):
            self.notify_user_by_id(uid)

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
        user.activate_timezone()
        # Prepare all parameters, in case they get modified when sending message asyncly
        # TODO: test those parameters
        message_params = {
            'user_id': uid,
            'template_id': '4Az0yqszw8TBJE9hLhjghZ4aA8HwYXM_VVr62wLnTUo',
            'url': self.get_absolute_url(full=True),
            'top_color': '#459ae9',
            'data': {
                "first": {
                    "value": '\U0001F552 %s' % self.title(),
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
                             + (('\n重复周期：' + self.get_repeat_text()) if self.has_repeat() else '')
                             + '\n\n点击详情可编辑本提醒',
                }
            },

        }
        if user.last_login and now() - user.last_login < timedelta(hours=48):
            raw_text = '\U0001F552 %s\n\n备注：%s\n时间：%s\n提醒：%s\n%s\n%s' % (
                self.title(),
                self.desc,
                self.local_time_string('Y/n/d(D) G:i'),
                self.nature_time_defer(),
                ('重复：' + self.get_repeat_text() + '\n') if self.has_repeat() else '',
                '<a href="%s">详情</a>' % self.get_absolute_url(True))
            message_params['raw_text'] = raw_text
        self.send_template_message_async(message_params, self.desc, user)

    @threads(10, timeout=60)
    def send_template_message_async(self, message_params, desc, user):
        uname = user.get_full_name()
        if 'raw_text' in message_params:
            try:
                res = wechat_client.message.send_text(message_params['user_id'], message_params['raw_text'])
                logger.info('Successfully send notification(%s) to user %s in text mode', desc, uname)
                return res
            except WeChatException as e:
                if e.errcode == 45015:
                    user.last_login = now() - timedelta(hours=49)
                    user.save(update_fields=['last_login'])
            except:
                logger.exception('Failed to send text notification(%s) to user %s', desc, uname)
        try:
            message_params.pop('raw_text', None)
            res = wechat_client.message.send_template(**message_params)
            logger.info('Successfully send notification(%s) to user %s in template mode', desc, uname)
            return res
        except WeChatException as e:
            logger.exception('Failed to send template notification(%s) to user %s', desc, uname)
            if e.errcode == 43101:
                user.unsubscribe()

    def add_participant(self, uid):
        if uid == self.owner_id or uid in self.participants:
            return False
        self.participants.append(uid)
        self.save(update_fields=['participants'])
        participant_modified.send(sender=self, participant=self.owner._default_manager.get(pk=uid), add=True)
        return True

    def remove_participant(self, uid):
        if uid not in self.participants:
            return
        self.participants.remove(uid)
        self.save(update_fields=['participants'])

    def has_repeat(self):
        if not self.repeat:
            return False
        has_positive = False
        for key in self.repeat:
            if self.repeat[key] > 0:
                has_positive = True
        return has_positive

    def get_repeat_text(self):
        # TODO: we don't support hour and minute now
        repeat_chinese_names = {REPEAT_KEY_YEAR: '年', REPEAT_KEY_MONTH: '月', REPEAT_KEY_DAY: '天',
                                REPEAT_KEY_WEEK: '周', REPEAT_KEY_HOUR: '小时', REPEAT_KEY_MINUTE: '分钟'}
        for key in self.repeat:
            repeat_count = self.repeat[key]
            if repeat_count:
                # First one wins
                return '每%s%s' % (
                        '' if repeat_count == 1 else repeat_count, repeat_chinese_names[key])

    def reschedule(self):
        # This method is idempotent
        if not self.has_repeat():
            return False
        _now = now()
        self.update_notify_time()
        if _now < self.notify_time:
            return False
        self.repeat.pop(REPEAT_KEY_MINUTE, None)  # No repeat every minute
        delta_params_map = {REPEAT_KEY_YEAR: 'years', REPEAT_KEY_MONTH: 'months', REPEAT_KEY_DAY: 'days',
                            REPEAT_KEY_WEEK: 'weeks', REPEAT_KEY_HOUR: 'hours', REPEAT_KEY_MINUTE: 'minutes'}
        delta = {}
        for key in self.repeat:
            delta[delta_params_map[key]] = self.repeat[key]

        last_notify_time = self.notify_time
        while self.notify_time <= _now:
            self.time += relativedelta(**delta)
            self.update_notify_time()
            if self.notify_time <= last_notify_time:
                logger.warn('Dead loop when rescheduling %s', self)
                return False
        return True

    def update_notify_time(self):
        # This method is idempotent
        self.notify_time = self.time + timedelta(minutes=self.defer)

    def subscribed_by(self, user):
        return self.owner_id == user.pk or user.pk in self.participants

    def get_absolute_url(self, full=False):
        if self.external_url:
            return self.external_url
        # url = reverse('remind-detail', kwargs={'pk': self.pk.hex})
        url = '/reminds/#/' + self.pk.hex
        if full:
            return urljoin(settings.HOST_NAME, url)
        return url

    def get_api_endpoint(self):
        return reverse('remind-detail', kwargs={'pk': self.pk.hex})

    def __unicode__(self):
        return '%s: %s (%s)' % (self.owner.get_full_name(), self.desc or self.event,
                                self.local_time_string('Y/n/j G:i:s'))


@receiver(pre_save, sender=Remind, dispatch_uid='update-notify-time')
def update_notify_time(instance, **kwargs):
    if instance.reschedule():
        instance.done = False
    instance.update_notify_time()


@receiver(participant_modified, dispatch_uid='notify-participant-modified')
def notify_participant_modified(sender, participant, add, **kwargs):
    if not sender.owner.notify_subscription:
        return
    settings_link = '\n<a href="%s">通知设置</a>' % urljoin(settings.HOST_NAME, '/reminds/#/settings')
    if add:
        notification = '\U0001F389 %s订阅了你的提醒：<a href="%s">%s</a>\n%s' % (
            participant.get_full_name(), sender.get_absolute_url(True), sender.title(), settings_link)
    else:
        notification = '\U0001F494 %s退出了你的提醒：<a href="%s">%s</a>\n%s' % (
            participant.get_full_name(), sender.get_absolute_url(True), sender.title(), settings_link)
    logger.info('Trying to notify user %s for participant modification on %s', sender.owner.get_full_name(), sender.desc)
    if sender.owner.last_login and now() - sender.owner.last_login < timedelta(hours=48):
        try:
            wechat_client.message.send_text(sender.owner_id, notification)
        except Exception as e:
            logger.info('Failed to notify user %s for participant modification, %s', participant.get_full_name(), e)
    else:
        logger.info('Ignore sending participant modification to %s, for inactivity for a long time', sender.owner.get_full_name())
