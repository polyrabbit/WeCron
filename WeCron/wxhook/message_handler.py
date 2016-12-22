#coding: utf-8
from __future__ import unicode_literals, absolute_import
import logging
import json

from datetime import timedelta
from django.utils import timezone
from wechatpy.replies import TextReply, TransferCustomerServiceReply

from django.contrib.auth import get_user_model
from .todo_parser import parse, ParseError

logger = logging.getLogger(__name__)


class WechatMessage(object):

    def __init__(self, message):
        self.message = message
        self.user = get_user_model().objects.get_or_fetch(message.source)

    @property
    def json_msg(self):
        return json.dumps(self.message._data, ensure_ascii=False, indent=2)

    def text_reply(self, reply_str):
        return TextReply(
            content=reply_str[:800],  # WeChat can only accept 2048 bytes of char
            message=self.message,
        ).render()

    def handle(self):
        logger.info('Get a %s %s from %s', getattr(self.message, 'event', ''),
                    self.message.type, self.user.nickname)
        handler = getattr(self, 'handle_%s' % self.message.type.lower(), self.handle_unknown)
        return handler()

    def handle_event(self):
        handler = getattr(self, 'handle_%s_event' % self.message.event.lower(), self.handle_unknown_event)
        return handler()

    def handle_text(self):
        try:
            reminder = parse(self.message.content, uid=self.message.source)
            reminder.owner = self.user
            reminder.save()
            reply_lines = [
                '/:ok将在%s提醒你%s' % (reminder.time_until(), reminder.event or ''),
                '\n备注: %s' % reminder.desc,
                '时间: %s' % reminder.local_time_string()
            ]
            if reminder.has_repeat():
                for idx, repeat_count in enumerate(reminder.repeat):
                    if repeat_count:
                        reply_lines.append('重复: 每%s%s' % (
                            '' if repeat_count==1 else repeat_count, reminder.repeat_names[idx]))
                        break
            reply_lines.append('\n<a href="%s">\U0001F449修改</a>' % reminder.get_absolute_url(True))
            return self.text_reply('\n'.join(reply_lines))
        except ParseError as e:
            return self.text_reply(unicode(e))
        except Exception as e:  # Catch all kinds of wired errors
            logger.exception('Semantic parse error')
            return self.text_reply(
                '\U0001F648抱歉，我还只是一个比较初级的定时机器人，理解不了您刚才所说的话：\n\n“%s”\n\n'
                '或者您可以换个姿势告诉我该怎么定时，比如这样：\n\n' 
                '“两个星期后提醒我去复诊”。\n'
                '“周五晚上提醒我打电话给老妈”。\n'
                '“1月22号提醒我给老婆买束花/:rose”。' % self.message.content
            )

    def handle_subscribe_event(self):
        self.user.subscribe = True
        self.user.save(update_fields=['subscribe'])
        return self.text_reply(
            'Dear %s，这是我刚注册的微信号，功能还在开发中，使用过程中如有不便请及时向我反馈哦。\n\n'
            '现在，直接输入文字或者语音就可以快速创建提醒啦！请点击下面的“使用方法”查看如何创建提醒。\n\n'
            'PS 这是一个开源项目，代码都在<a href="https://github.com/polyrabbit/WeCron">这里</a>\U0001F517，欢迎有开发技能的同学参与进来！'
            % self.user.get_full_name()
        )

    def handle_unsubscribe_event(self):
        self.user.subscribe = False
        self.user.save(update_fields=['subscribe'])
        return self.text_reply("Bye")

    def handle_unknown(self):
        return self.text_reply(
            '/:jj如需设置提醒，只需用语音或文字告诉我就行了，比如这样：\n\n' 
            '“两个星期后提醒我去复诊”。\n'
            '“周五晚上提醒我打电话给老妈”。\n'
            '“1月22号提醒我给老婆买束花/:rose”。'
        )

    def handle_unknown_event(self):
        return self.handle_unknown()
        # return self.text_reply(
        #     'Hi %s! your %s event is\n%s' % (
        #         self.user.get_full_name(), self.message.event.lower(), self.json_msg)
        # )

    def handle_voice(self):
        self.message.content = getattr(self.message, 'recognition', '')
        if not self.message.content:
            return self.text_reply(
                '\U0001F648哎呀，看起来微信的语音转文字功能又双叒叕罬蝃抽风了，请重试一遍，或者直接发文字给我~'
            )
        return self.handle_text()

    def handle_location_event(self):
        return self.text_reply('\U0001F4AA基于地理位置的提醒正在开发中，敬请期待~\n' + self.json_msg)

    handle_location = handle_location_event

    def handle_click_event(self):
        if self.message.key.lower() == 'time_remind_today':
            now = timezone.now()
            time_reminds = self.user.get_time_reminds().filter(time__date=now).order_by('time').all()
            remind_text_list = self.format_wechat_remind_list(time_reminds)
            if remind_text_list:
                return self.text_reply('/:sunHi %s, 你今天的提醒有:\n\n%s' % (self.user.get_full_name(),
                                                                       '\n'.join(remind_text_list)))
            return self.text_reply('/:coffee今天没有提醒，休息一下吧！')
        elif self.message.key.lower() == 'time_remind_tomorrow':
            tomorrow = timezone.now()+timedelta(days=1)
            time_reminds = self.user.get_time_reminds().filter(time__date=tomorrow).order_by('time').all()
            remind_text_list = self.format_wechat_remind_list(time_reminds, True)
            if remind_text_list:
                return self.text_reply('/:sunHi %s, 你明天的提醒有:\n\n%s' % (self.user.get_full_name(),
                                                                       '\n'.join(remind_text_list)))
            return self.text_reply('/:coffee明天还没有提醒，休息一下吧！')
        return self.handle_unknown_event()

    def format_wechat_remind_list(self, reminds, next_run_found=False):
        now = timezone.now()
        remind_text_list = []
        for rem in reminds:
            emoji = '\U0001F552'  # Clock
            # takewhile is too aggressive
            if rem.time < now:
                emoji = '\U00002713 ' # Done
            elif not next_run_found:
                next_run_found = True
                emoji = '\U0001F51C' # Soon
            remind_text_list.append('%s %s - <a href="%s">%s</a>' %
                                    (emoji, rem.local_time_string('G:i'), rem.get_absolute_url(True), rem.title()))
        return remind_text_list


def handle_message(msg):
    # TODO unique based on msgid
    return WechatMessage(msg).handle()

