# coding: utf-8
from __future__ import unicode_literals, absolute_import
import logging
import requests
import time

from django.db.models import Q
from django.core.management import BaseCommand
from django.utils import timezone
from django.utils.dateparse import parse_datetime
from eosram.models import PriceThresholdChange, PricePercentageChange, PriceHistory, Profile


logger = logging.getLogger(__name__)
EOS_ACCOUNT = 'bitcoinrocks'
UA = 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_13_6) AppleWebKit/537.36 (KHTML, like Gecko) ' \
     'Chrome/67.0.3396.99 Safari/537.36'


def update_recharge_history():
    # resp = requests.post('https://api.eosflare.io/chain/get_actions',
    #                      {"_url": "/chain/get_actions", "_method": "POST",
    #                       "_headers": {"content-type": "application/json"}, "account": EOS_ACCOUNT, "lang": "zh-CN"},
    #                      headers={'User-Agent': UA, 'Referer': 'https://eosflare.io/account/%s' % EOS_ACCOUNT})
    # resp.raise_for_status()
    resp = requests.post('http://api1.eosasia.one/v1/history/get_actions',
                         json={"account_name": EOS_ACCOUNT},
                         headers={'User-Agent': UA})
    resp.raise_for_status()
    for action in resp.json().get('actions', []):
        act = action.get('action_trace', {}).get('act', {})
        if 'eosio.token' != act.get('account', '').lower() \
                or 'transfer' != act.get('name', '').lower() \
                or act.get('data', {}).get('to') != EOS_ACCOUNT:
            continue
        memo = act.get('data', {}).get('memo')
        if not memo:
            continue
        user_profile = Profile.objects.filter(memo=memo).first()
        if not user_profile:
            continue
        block_time = parse_datetime(action.get('block_time', '') + 'Z')
        if user_profile.last_update >= block_time:
            continue
        quantity = act.get('data', {}).get('quantity', '').replace(' EOS', '')
        if not quantity.replace('.', '', 1).isdigit():
            continue
        user_profile.last_update = block_time
        user_profile.recharge += float(quantity)
        user_profile.save()


def alert_user(user, title, content, additional=''):
    user_profile = Profile.objects.filter(owner=user).first()
    if not user_profile:
        user_profile = Profile(owner=user)
        user_profile.save()
    user_profile.send_wechat_notification(title, content, additional)


def get_ram_price():
    resp = requests.post('http://35.227.201.66/v1/getram/ramprices', headers={'User-Agent': UA, 'Referer': 'http://southex.com/'})
    resp.raise_for_status()
    return resp.json()


def toggle_abs_price_alert(price):
    queryset = PriceThresholdChange.objects.filter(threshold__isnull=False)\
        .filter(Q(done=False, threshold__lte=price, increase=True)
                | Q(done=False, threshold__gte=price, increase=False))
    for change in queryset:
        title = 'EOS Ram价格' + ('上涨' if change.increase else '下跌') + ('超过%s' % change.threshold)
        alert_user(change.owner, title, '当前价格 %s' % price, '提醒价格：%s' % change.threshold)
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
                               '当前价格 %s' % price, '当前波动：%.2f%%' % change_pct)
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
            update_recharge_history()
            time.sleep(12)