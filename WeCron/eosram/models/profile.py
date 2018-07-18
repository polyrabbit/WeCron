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
from common import wechat_client
from wechatpy.utils import random_string

RATIO = 1.0/500
logger = logging.getLogger(__name__)


def generate_memo():
    return random_string(20)


class Profile(models.Model):

    memo = models.CharField('充值码', primary_key=True, max_length=64, default=generate_memo)

    owner = models.ForeignKey(settings.AUTH_USER_MODEL, verbose_name='用户',
                              related_name='eosram_profile', on_delete=models.CASCADE)
    recharge = models.FloatField('已充值数额', default=20*RATIO)
    used = models.IntegerField('已使用的提醒次数', default=0)
    last_update = models.DateTimeField('上次更新充值数额时间', default=now)

    class Meta:
        # ordering = ["time"]
        db_table = 'eosram_price_profile'

    def has_quota(self):
        return self.used < self.recharge/RATIO

    def available_quota(self):
        return self.recharge/RATIO - self.used

    @threads(10, timeout=60)  # async function
    def send_wechat_notification(self, title, content, additional=''):
        uname = self.owner.get_full_name()
        if not self.owner.subscribe:
            logger.info('User %s has unsubscribed, skip sending notification' % uname)
            return

        if not self.has_quota():
            logger.info('User(%s) has no sufficient quota for this notification, charged %f EOS',
                        uname, (self.recharge - Profile._meta.get_field('recharge').get_default()))

        if self.available_quota() < 10:
            additional += '\n剩余提醒：%s次\n\n为避免接受不到提醒，请点击详情尽快充值EOS' % self.available_quota()
        else:
            additional += '\n\n点击详情更改提醒价格'
        message_params = {
            'user_id': self.owner.pk,
            'template_id': '2piojX2y-fxOFiNeVaLahNItiKaeVaZENnRd1_cpwYQ',
            'url': urljoin(settings.HOST_NAME, reverse('ram_index') + '?from=notification'),
            'top_color': '#459ae9',
            'data': {
                "first": {
                    "value": '\U0001F552 %s\n' % title,
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
            logger.info('Successfully send notification(%s) to user %s in template mode', title, uname)
            return res
        except:
            logger.exception('Failed to send notification(%s) to user %s', title, uname)