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
                {"url": "http://wecron.betacat.io/reminds/#/settings", "type": "view", "name": "设置", "sub_button": []},
                {"url": "http://wecron.betacat.io/reminds/", "type": "view", "name": "所有提醒", "sub_button": []},
                {"type": "click", "name": "明天", "key": "time_remind_tomorrow", "sub_button": []},
                {"type": "click", "name": "今天", "key": "time_remind_today", "sub_button": []}]},
            {"type": "click", "name": "使用方法", "key": "time_remind_create", "sub_button": []},
            {"name": "亲友团",   "sub_button": [
                {"type": "view", "name": "\U0001F60A意见反馈", "url": "https://www.sojump.hk/jq/15914889.aspx"},
                {"type": "view", "name": "©源代码", "url": "https://github.com/polyrabbit/WeCron"},
                {"type": "click", "name": "小密圈", "key": "join_group"},
                # {"type": "click", "name": "作者微信", "key": "add_friend"},
                {"type": "click", "name": "赞赏", "key": "donate_geizang"}
            ]}
        ]}
        self.stdout.write(
                json.dumps(wechat_client.menu.create(new_menu),
                indent=2,
                ensure_ascii=False))

# wechat_client.message.send_template(
#     user_id='owQF1v2jgcmoINYC-RE2AzhuATq0',
#     template_id='OHwCU_UbAW3XoaLJimwMzbc7RFQMCEX0OBZ4PvsDTuk',
#     url='http://wecron.betacat.io/reminds/#/settings',
#     top_color='#459ae9',
#     data={
#         "first": {
#             "value": '微定时更新',
#             "color": "#459ae9"
#         },
#         "keyword1": {
#             "value": '喵小咪',
#         },
#         "keyword2": {
#             "value": '根据亲的反馈，本次更新主要增加了对不同时区的支持，让海外用户也能愉快的使用微定时。',
#         },
#         'remark': {
#             'value': '\n欢迎试用并提出您的宝贵意见！'
#         }
#     },
# )