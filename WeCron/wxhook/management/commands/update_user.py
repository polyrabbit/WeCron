# coding: utf-8
from __future__ import unicode_literals, absolute_import

from django.core.management import BaseCommand
from django.contrib.auth import get_user_model
from common import wechat_client


class Command(BaseCommand):

    def handle(self, *args, **options):
        user_manager = get_user_model().objects
        user_id_list = user_manager.filter(subscribe=True, last_login__isnull=False)\
                           .order_by('-last_login').values_list('openid', flat=True)[:90]
        for user_info in wechat_client.user.get_batch(user_id_list):
            user_manager.filter(openid=user_info['openid']).update(**user_manager.amend_model_params(**user_info))
