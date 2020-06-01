# coding: utf-8
from __future__ import unicode_literals
import logging
from urlparse import urljoin

from tomorrow import threads
from django.utils.timezone import now
from django.db import models
from django.conf import settings
from django.core.urlresolvers import reverse
from django.utils import timezone
from django.utils.formats import date_format
from django.contrib.auth import get_user_model
from common import wechat_client
from wechatpy.utils import random_string

RATIO = 1.0/500
INVITE_REWARD = 10
logger = logging.getLogger(__name__)


def generate_memo():
    return random_string(16)


class Profile(models.Model):

    memo = models.CharField('充值码', primary_key=True, max_length=64, default=generate_memo)

    # owner = models.ForeignKey(settings.AUTH_USER_MODEL, verbose_name='用户', null=True,
    #                           related_name='eosram_profile', on_delete=models.CASCADE)
    owner_id = models.CharField(max_length=40, db_index=True, null=True)
    ref = models.CharField('邀请者', max_length=64, null=True)
    reward = models.IntegerField('奖励次数', default=20)
    recharge = models.FloatField('已充值数额', default=0)
    used = models.IntegerField('已使用的提醒次数', default=0)
    last_update = models.DateTimeField('上次更新充值数额时间', default=now)
    eos_account = models.CharField('EOS账户', max_length=32, null=True)

    class Meta:
        # ordering = ["time"]
        db_table = 'eosram_price_profile'

    def has_quota(self):
        return self.used - self.reward < self.recharge/RATIO

    def available_quota(self):
        return self.recharge/RATIO + self.reward - self.used

    @threads(10, timeout=60)  # async function
    def send_wechat_alert(self, title, content, additional=''):
        owner = get_user_model().objects.filter(pk=self.owner_id).first()
        if not owner:
            logger.info('User id %s not found, skip sending ram price alert' % self.owner_id)
            return

        uname = owner.get_full_name()
        if not owner.subscribe:
            logger.info('User %s has unsubscribed, skip sending ram price alert' % uname)
            return

        if not self.has_quota():
            logger.info('User(%s) has no sufficient quota for this notification, charged %f EOS',
                        uname, (self.recharge - Profile._meta.get_field('recharge').get_default()))
            return

        if self.available_quota() < 10:
            additional += '\n剩余提醒：%d次\n\n为避免接受不到提醒，请点击详情尽快充值EOS' % self.available_quota()
        else:
            additional += '\n\n点击详情更改提醒价格'
        message_params = {
            'user_id': owner.pk,
            'template_id': '2piojX2y-fxOFiNeVaLahNItiKaeVaZENnRd1_cpwYQ',
            'url': urljoin(settings.HOST_NAME, reverse('ram_index') + '?from=notification'),
            'top_color': '#459ae9',
            'data': {
                "first": {
                    "value": '\U000026A0 %s\n' % title,
                    "color": "#459ae9"
                },
                "keyword1": {
                    "value": date_format(timezone.localtime(timezone.now()), format='n月j日 G:i', use_l10n=True),
                },
                "keyword2": {
                    "value": content,
                },
                "remark": {
                    "value": additional,
                }
            }
        }

        try:
            res = wechat_client.message.send_template(**message_params)
            self.used += 1
            self.save(update_fields=['used'])
            logger.info('Successfully send ram price alert(%s) to user %s', title, uname)
            return res
        except:
            logger.exception('Failed to send ram price alert(%s) to user %s', title, uname)

    def add_reward(self, invitee, quant=INVITE_REWARD):
        self.reward += quant
        self.save(update_fields=['reward'])

        owner = get_user_model().objects.filter(pk=self.owner_id).first()
        if not owner:
            logger.info('User id %s not found, skip sending invite award' % self.owner_id)
            return
        logger.info('%s invites %s', self.get_name(), invitee.get_name())
        uname = owner.get_full_name()
        if not owner.subscribe:
            logger.info('User %s has unsubscribed, skip sending invite award' % uname)
            return

        try:
            raw_text = '\U00002764 新的提醒奖励\n\n奖励次数：%s次\n邀请朋友：%s\n\n%s' % (
                quant, invitee.get_name(),
                '<a href="%s">详情</a>' % urljoin(settings.HOST_NAME, reverse('ram_index') + '?from=invite'))
            res = wechat_client.message.send_text(owner.pk, raw_text)
            logger.info('Successfully send ram price invite award notification to user %s in text mode', uname)
            return res
        except:
            logger.exception('Failed to send invite award notification to user %s', uname)


    def get_name(self):
        UserModel = get_user_model()
        try:
            return UserModel.objects.get(pk=self.owner_id).get_full_name()
        except UserModel.DoesNotExist:
            return '未知'