# coding: utf-8
from __future__ import unicode_literals, absolute_import

import logging
from django.core.management import BaseCommand
from django.contrib.auth import get_user_model
from django.utils import timezone

from remind.models import Remind
from common import wechat_client
from wxhook.message_handler import WechatMessage

logger = logging.getLogger(__name__)


class Command(BaseCommand):

    def handle(self, *args, **options):
        now = timezone.now()
        today_reminds = Remind.objects.filter(time__date=now).all()
        users_to_notify = set()
        for rem in today_reminds:
            users_to_notify.add(rem.owner_id)
            users_to_notify.update(rem.participants)

        time_threshold = now - timezone.timedelta(hours=48)
        for uid in users_to_notify:
            user = get_user_model().objects.filter(pk=uid, subscribe=True, last_login__gt=time_threshold).first()
            if not user:
                continue
            # Get today's reminds of a user
            user_today_reminds = list(user.get_time_reminds().filter(time__date=now).order_by('time').all())
            for rem in user_today_reminds:
                # Add 2 minutes delta so user won't get two consecutive notice
                if rem.time > now + timezone.timedelta(minutes=2):
                    break
            else:
                # If all reminds are passed, we should not send the greeting
                continue
            remind_text_list = WechatMessage.format_remind_list(user_today_reminds)
            if not remind_text_list:
                continue
            morning_greeting = '/:sun早上好%s, 你今天的提醒有:\n\n%s' % (
                user.get_full_name(),
                '\n'.join(remind_text_list))
            try:
                wechat_client.message.send_text(user.openid, morning_greeting)
                logger.info('Send %s morning greeting to %s', len(remind_text_list), user.get_full_name())
            except Exception as e:
                logger.info('Failed to send morning greeting to user %s, %s', user.get_full_name(), e)
