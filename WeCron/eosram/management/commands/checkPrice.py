# coding: utf-8
from __future__ import unicode_literals, absolute_import
import logging
import requests
import time
import random

from django.db.models import Q
from django.core.management import BaseCommand
from django.utils import timezone
from django.utils.dateparse import parse_datetime
from eosram.models import PriceThresholdChange, PricePercentageChange, PriceHistory, Profile


logger = logging.getLogger(__name__)
EOS_ACCOUNT = 'bitcoinrocks'
UA = 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_13_6) AppleWebKit/537.36 (KHTML, like Gecko) ' \
     'Chrome/67.0.3396.99 Safari/537.36'

# See https://www.eosdocs.io/resources/apiendpoints/
BP_API_POOL = [
    # 'https://api.eosnewyork.io',
    # 'https://api1.eosasia.one',
    # 'http://api.hkeos.com:80',
    'https://api.eosdetroit.io:443',
    'https://publicapi-mainnet.eosauthority.com',
    # 'http://api1.eosdublin.io:80',
    'https://eos.greymass.com',
]


def update_recharge_history():
    BP_API = random.choice(BP_API_POOL)
    resp = requests.post(BP_API + '/v1/history/get_actions',
                         json={"account_name": EOS_ACCOUNT},
                         headers={'User-Agent': UA}, timeout=10)
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
        # Recharge happened
        quantity = act.get('data', {}).get('quantity', '').replace(' EOS', '')
        if not quantity.replace('.', '', 1).isdigit():
            continue
        user_profile.last_update = block_time
        user_profile.eos_account = act.get('data', {}).get('from')
        user_profile.recharge += float(quantity)
        user_profile.save()
        logger.info('User(%s) recharges %s EOS', user_profile.get_name(), quantity)


def alert_user(user, title, content, additional=''):
    user_profile = Profile.objects.filter(owner_id=user.pk).first()
    if not user_profile:
        user_profile = Profile.objects.create(owner_id=user.pk)
    user_profile.send_wechat_alert(title, content, additional)

# Back up
def get_ram_price2():
    resp = requests.post('http://35.227.201.66/v1/getram/ramprices',
                         headers={'User-Agent': UA, 'Referer': 'http://southex.com/'},
                         timeout=10)
    resp.raise_for_status()
    return resp.json()['p']


def get_ram_price():
    BP_API = random.choice(BP_API_POOL)
    resp = requests.post(BP_API + '/v1/chain/get_table_rows',
                         json={"json":"true","code":"eosio","scope":"eosio","table":"rammarket","limit":"10"},
                         headers={'User-Agent': UA}, timeout=10)
    resp.raise_for_status()
    ram_market = resp.json()['rows'][0]
    base = float(ram_market['base']['balance'].split(' ')[0])
    quote = float(ram_market['quote']['balance'].split(' ')[0])
    return quote / base * 1024


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

            if (change.increase and change_pct >= change.threshold) \
                    or (not change.increase and change_pct*-1 > change.threshold):
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


def check_ram_price():
    price = get_ram_price()
    logger.info('Current price is %f' % price)
    toggle_abs_price_alert(price)
    toggle_price_percent_change(price)


class Command(BaseCommand):

    def handle(self, *args, **options):
        while True:
            check_ram_price()
            update_recharge_history()
            time.sleep(30)
