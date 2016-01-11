#coding: utf-8
from __future__ import unicode_literals, absolute_import
import logging
import json

from django.utils import timezone
from wechatpy.replies import TextReply, TransferCustomerServiceReply

from common import wechat_client
from .models import User
from .semantic_parser import parse

logger = logging.getLogger(__name__)


class WechatMessage(object):

    def __init__(self, message):
        self.message = message
        self.user = User.objects.get_or_fetch(message.source)

    @property
    def json_msg(self):
        return json.dumps(self.message._data, ensure_ascii=False, indent=2)

    def text_reply(self, reply_str):
        return TextReply(
            content=reply_str[:800],  # WeChat can only accept 2048 bytes of char
            message=self.message,
        ).render()

    def handle(self):
        logger.info('Get a %s from %s', self.message.type.lower(), self.user.nickname)
        handler = getattr(self, 'handle_%s' % self.message.type.lower(), self.handle_unknown)
        return handler()

    def handle_event(self):
        handler = getattr(self, 'handle_event_%s' % self.message.event.lower(), self.handle_event_unknown)
        return handler()

    def handle_text(self):
        try:
            reminder = parse(self.message.content, uid=self.message.source)
            reminder.owner = self.user
            reminder.save()
            return self.text_reply(
                '/:ok将在%s提醒你%s\n\n描述: %s\n提醒时间: %s\n\n<a href="%s">查看详情</a>' % (
                    reminder.nature_time(), reminder.event or '',
                    reminder.desc, reminder.local_time_string(),
                    reminder.get_absolute_url())
            )
        except ValueError as e:
            return self.text_reply(unicode(e))
        except Exception as e:  # Catch all kinds of wired errors
            logger.exception('Semantic parse error')
            return self.text_reply(
                '\U0001F648抱歉，我还只是一个比较初级的定时机器人，理解不了您刚才所说的话：\n\n“%s”\n\n'
                '或者您可以换个姿势告诉我该怎么定时，比如这样：\n\n' 
                '“五分钟后提醒我该起锅了”。\n'
                '“周五晚上提醒我打电话给老妈”。\n'
                '“1月22号上午提醒我给女朋友买束花/:rose”。' % self.message.content
            )

    def handle_event_subscribe(self):
        return self.text_reply(
            'Dear %s，这是我刚注册的微信号，功能还在开发中，使用过程中如有不便请及时向我反馈哦。\n\n'
            '现在，直接输入文字或者语音就可以快速创建提醒啦~ 您可以这样说：\n\n'
            '“五分钟后提醒我该起锅了”。\n'
            '“周五晚上提醒我打电话给老妈”。\n'
            '“1月22号上午提醒我给女朋友买束花/:rose”。\n\n'
            '现在就来试试吧！'
            % self.user.get_full_name()
        )

    def handle_unknown(self):
        return self.text_reply(
            '/:jj如需设置提醒，只需用语音或文字告诉我就行了，比如这样：\n\n' 
            '“五分钟后提醒我该起锅了”。\n'
            '“周五晚上提醒我打电话给老妈”。\n'
            '“1月22号上午提醒我给女朋友买束花/:rose”。'
        )

    def handle_event_unknown(self):
        return self.handle_unknown()
        # return self.text_reply(
        #     'Hi %s! your %s event is\n%s' % (
        #         self.user.get_full_name(), self.message.event.lower(), self.json_msg)
        # )

    def handle_voice(self):
        self.message.content = getattr(self.message, 'recognition', '') or ''
        return self.handle_text()

    def handle_event_location(self):
        return self.text_reply('\U0001F4AA基于地理位置的提醒正在开发中，敬请期待~\n' + self.json_msg)

    handle_location = handle_event_location

    def handle_event_click(self):
        if self.message.key.lower() == 'time_remind_today':
            now = timezone.now()
            time_reminds = self.user.get_time_reminds().filter(time__date=now).order_by('time').all()
            remind_text_list = []
            next_run_found = False
            for rem in time_reminds:
                emoji = '\U0001F552'
                # takewhile is too aggressive
                if rem.time < now:
                    emoji = '\U00002713 '
                elif not next_run_found:
                    next_run_found = True
                    emoji = '\U0001F51C'

                remind_text_list.append('%s %s - %s' % (emoji, rem.local_time_string('%H:%M'), rem.title()))

            if remind_text_list:
                return self.text_reply('/:sunHi %s, 你今天的提醒有:\n\n%s' % (self.user.get_full_name(),
                                                                       '\n'.join(reversed(remind_text_list))))
            return self.text_reply('/:coffee今天没有提醒，休息一下吧！')
        return self.handle_event_unknown()


def handle_message(msg):
    # TODO unique based on msgid
    return WechatMessage(msg).handle()

