# coding: utf-8
from __future__ import absolute_import
from collections import namedtuple

from django.core.management import BaseCommand
from django.utils import timezone
from django.db import connection

from wechat_user.models import WechatUser

twin_query = '''select new_user.openid as new_id, old_user.openid as old_id from "user" as new_user
inner join "user" as old_user on (new_user.openid!=old_user.openid and old_user.source is not null and new_user.nickname=old_user.nickname
and new_user.sex=old_user.sex and new_user.city=old_user.city and new_user.country=old_user.country
and new_user.province=old_user.province and new_user.language=old_user.language and new_user.timezone=old_user.timezone)
where "new_user".nickname=%s and "new_user"."source" is null 
and exists (select * from time_remind where time_remind.owner_id=old_user.openid)'''


def namedtuplefetchall(cursor):
    "Return all rows from a cursor as a namedtuple"
    desc = cursor.description
    nt_result = namedtuple('Result', [col[0] for col in desc])
    return [nt_result(*row) for row in cursor.fetchall()]


class Command(BaseCommand):
    help = 'Sync user history by nick name'

    def add_arguments(self, parser):
        parser.add_argument('nickname', nargs='?', type=str)
        parser.add_argument('--since-yesterday', action='store_true', help='sync active users since yesterday')

    def handle(self, *args, **options):
        if options['nickname'] is not None:
            self.sync_user_history(options['nickname'])
        elif options['since_yesterday'] == True:
            yesterday = timezone.now() - timezone.timedelta(days=2)
            recent_users = WechatUser.objects.filter(subscribe_time__gte=yesterday, source__isnull=True).all()
            for u in recent_users:
                self.sync_user_history(u.nickname, u.openid)
        else:
            raise ValueError("invalid arguments")

    def sync_user_history(self, nickname, openid=None):
        with connection.cursor() as cursor:
            params = [nickname]
            query = twin_query
            if openid is not None:
                query += ' and new_user.openid=%s'
                params.append(openid)
            cursor.execute(query, params)
            twins_qs = namedtuplefetchall(cursor)
            if len(twins_qs) == 0:
                print 'no twins found matching nickname=%s' % nickname
            elif len(twins_qs) != 1:
                raise RuntimeError('found %d twins for %s, ambiguous!\nsql: \n%s' % (len(twins_qs), nickname, twin_query))
            else:
                twins = twins_qs[0]
                cursor.execute('update time_remind set owner_id=%s where owner_id=%s', [twins.new_id, twins.old_id])
                print 'migrate %s(%s -> %s), records %d' % (nickname, twins.old_id, twins.new_id, cursor.rowcount)
