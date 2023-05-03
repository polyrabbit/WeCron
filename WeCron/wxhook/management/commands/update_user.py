# coding: utf-8
from __future__ import unicode_literals, absolute_import

import time
import random

from django.core.management import BaseCommand
from django.contrib.auth import get_user_model
from django.db import connection
from django.db.utils import DatabaseError
from common import wechat_client
from wechatpy import WeChatClientException

BATCH_SIZE = 90


class Command(BaseCommand):

    def handle(self, *args, **options):
        self.check_subscribtion()
        self.clear_reminds()
        self.clear_user()

    def clear_reminds(self):
        with connection.cursor() as cursor:
            try:
                cursor.execute('delete from time_remind r where not exists(select * from "user" where r.owner_id="user".openid and "user".subscribe=true)')
                print 'deleted %d reminds' % cursor.rowcount
            except DatabaseError as e:
                print e

    def clear_user(self):
        with connection.cursor() as cursor:
            try:
                cursor.execute('delete from "user" where subscribe=false')
                print 'deleted %d users' % cursor.rowcount
            except DatabaseError as e:
                print e

    def check_subscribtion(self):
        start = time.time()
        user_manager = get_user_model().objects
        total_size = user_manager.count()
        updated = 0
        unsubscribed = 0
        for _ in range(10):
            offset = random.randint(0, total_size)
            user_id_list = user_manager.filter(subscribe=True, source__isnull=True).values_list('openid', flat=True)[
                           offset:offset + BATCH_SIZE]
            print user_id_list.query
            if len(user_id_list) == 0:
                continue
            try:
                user_info_list = wechat_client.user.get_batch(user_id_list)
            except WeChatClientException as e:
                print e
                continue
            for user_info in user_info_list:
                updated += user_manager.filter(openid=user_info['openid']).update(**user_manager.amend_model_params(**user_info))
                if not user_info['subscribe']:
                    unsubscribed += 1

        print 'updated %d users, unsubscribed %d, cost(s): %f' % (updated, unsubscribed, time.time()-start)
