# coding: utf-8
import time

from django.contrib.auth import get_user_model
from django.core.management import BaseCommand, CommandError
from wechatpy import WeChatClientException

from common import wechat_client

BATCH_SIZE = 100  # Limit of user/info/batchget


class Command(BaseCommand):
    help = 'Backfill UnionID of subscribed users from the official account'

    def add_arguments(self, parser):
        parser.add_argument('--limit', type=int, default=0, help='Max users to process, 0 for all')
        parser.add_argument('--sleep', type=float, default=0.2, help='Seconds to sleep between batches')

    def handle(self, *args, **options):
        user_manager = get_user_model().objects
        queryset = user_manager.filter(subscribe=True, unionid__isnull=True, source__isnull=True).order_by('openid')
        limit = options['limit']
        start = time.time()
        processed = updated = 0
        last_openid = ''
        while not limit or processed < limit:
            size = BATCH_SIZE if not limit else min(BATCH_SIZE, limit - processed)
            openids = list(queryset.filter(openid__gt=last_openid).values_list('openid', flat=True)[:size])
            if not openids:
                break
            last_openid = openids[-1]
            processed += len(openids)
            try:
                user_info_list = wechat_client.user.get_batch(openids)
            except WeChatClientException as e:
                # The cursor has already moved on, so this batch would be skipped silently
                raise CommandError('Failed to fetch the batch after %s: %s' % (openids[0], e))
            for info in user_info_list:
                if info.get('unionid'):
                    updated += user_manager.filter(openid=info['openid']).update(unionid=info['unionid'])
            time.sleep(options['sleep'])
        self.stdout.write('Processed %d users, got UnionID for %d, cost(s): %.1f' % (
            processed, updated, time.time() - start))
