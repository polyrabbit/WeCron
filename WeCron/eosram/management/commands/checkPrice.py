# coding: utf-8
from __future__ import unicode_literals, absolute_import
import logging
import requests
import time
from urlparse import urljoin

from tomorrow import threads
from django.db.models import Q
from django.core.management import BaseCommand
from django.core.urlresolvers import reverse
from django.conf import settings
from django.utils import timezone
from django.utils.formats import date_format
from eosram.models import PriceThresholdChange, PricePercentageChange, PriceHistory
from common import wechat_client


logger = logging.getLogger(__name__)
EOS_ACCOUNT = 'miaochangxin'
UA = 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_13_6) AppleWebKit/537.36 (KHTML, like Gecko) ' \
     'Chrome/67.0.3396.99 Safari/537.36'


def get_transactions():
    resp = requests.post('https://api.eosflare.io/chain/get_actions',
                         {"_url": "/chain/get_actions", "_method": "POST",
                          "_headers": {"content-type": "application/json"}, "account": EOS_ACCOUNT, "lang": "zh-CN"},
                         headers={'User-Agent': UA, 'Referer': 'https://eosflare.io/account/%s' % EOS_ACCOUNT})
    resp.raise_for_status()
    return resp.json()


def get_ram_price():
    resp = requests.post('http://35.227.201.66/v1/getram/ramprices', headers={'User-Agent': UA, 'Referer': 'http://southex.com/'})
    resp.raise_for_status()
    return resp.json()


@threads(10, timeout=60)
def send_wechat_notification_async(message_params, title, uname):
    try:
        res = wechat_client.message.send_template(**message_params)
        logger.info('Successfully send notification(%s) to user %s in template mode', title, uname)
        return res
    except:
        logger.exception('Failed to send notification(%s) to user %s', title, uname)


def alert_user(user, title, content, additional=''):
    if not user.subscribe:
        logger.info('User %s has unsubscribed, skip sending notification' % user.get_full_name())
        return
    message_params = {
        'user_id': user.pk,
        'template_id': '2piojX2y-fxOFiNeVaLahNItiKaeVaZENnRd1_cpwYQ',
        'url': urljoin(settings.HOST_NAME, reverse('ram_index')),
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
                "value": additional + '\n\n点击详情更改提醒价格',
            }
        }

    }
    return send_wechat_notification_async(message_params, title, user.get_full_name())


def toggle_abs_price_alert(price):
    queryset = PriceThresholdChange.objects.filter(threshold__isnull=False)\
        .filter(Q(done=False, threshold__lte=price, increase=True)
                | Q(done=False, threshold__gte=price, increase=False))
    for change in queryset:
        title = 'EOS Ram价格' + ('上涨' if change.increase else '下跌')
        alert_user(change.owner, title, '当前价格 %s' % price, '提醒价格：%s' %change.threshold)
        change.done = True
        change.save(update_fields=['done'])

    PriceThresholdChange.objects.filter(threshold__isnull=False)\
        .filter(Q(done=True, threshold__lte=price, increase=False)
                | Q(done=True, threshold__gte=price, increase=True)).update(done=False)


def toggle_price_percent_change(price):
    now = timezone.now()
    PriceHistory(time=now, price=price).save()
    # Remove old price
    hours_ago = now - timezone.timedelta(hours=2)
    PriceHistory.objects.filter(time__lt=hours_ago).delete()

    for change in PricePercentageChange.objects.filter(threshold__isnull=False):
        minutes_ago = now - timezone.timedelta(minutes=change.period)
        price_pivot = PriceHistory.objects.filter(time__range=(minutes_ago-timezone.timedelta(minutes=1), minutes_ago))\
            .order_by('time').first()
        if price_pivot:
            change_pct = 100.0 * (price - price_pivot.price) / price_pivot.price

            if abs(change_pct) >= abs(change.threshold):
                if not change.done:
                    period_for_human = '%s分钟' % change.period
                    if change.period % 60 == 0:
                        period_for_human = '%s小时' % (change.period / 60)
                    increase_for_human = '上涨' if change.increase else '下跌'

                    alert_user(change.owner, 'EOS Ram价格%s内%s超过%s%%' % (period_for_human, increase_for_human, change.threshold),
                               '当前价格 %s' % price,
                               '当前波动：%.2f%%' % change_pct)
                    change.done = True
                    change.save(update_fields=['done'])
            elif change.done:
                change.done = False
                change.save(update_fields=['done'])


def check_price():
    price = get_ram_price()
    current_price = float(price['p'])
    logger.info('Current price is %f' % current_price)
    toggle_abs_price_alert(current_price)
    toggle_price_percent_change(current_price)


class Command(BaseCommand):

    def handle(self, *args, **options):
        while True:
            check_price()
            time.sleep(12)