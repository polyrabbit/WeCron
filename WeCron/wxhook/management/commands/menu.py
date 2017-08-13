# coding: utf-8
from __future__ import unicode_literals, absolute_import

import json
from django.core.management import BaseCommand
from common import wechat_client


class Command(BaseCommand):

    def add_arguments(self, parser):
        parser.add_argument('new_menu', nargs='*')

    def handle(self, *args, **options):
        new_menu = {"button": [
            {"name": "我的提醒", "sub_button": [
                {"url": "http://wecron.betacat.io/reminds/", "type": "view", "name": "所有提醒", "sub_button": []},
                {"type": "click", "name": "明天", "key": "time_remind_tomorrow", "sub_button": []},
                {"type": "click", "name": "今天", "key": "time_remind_today", "sub_button": []}]},
            {"type": "click", "name": "使用方法", "key": "time_remind_create", "sub_button": []},
            {"name": "亲友团",   "sub_button": [
                {"type": "view", "name": "\U0001F60A意见反馈", "url": "https://www.sojump.hk/jq/15914889.aspx"},
                {"type": "click", "name": "小密圈", "key": "join_group"},
                # {"type": "click", "name": "作者微信", "key": "add_friend"},
                {"type": "click", "name": "赞赏", "key": "donate"}
            ]}
        ]}
        self.stdout.write(
                json.dumps(wechat_client.menu.create(new_menu),
                indent=2,
                ensure_ascii=False))
