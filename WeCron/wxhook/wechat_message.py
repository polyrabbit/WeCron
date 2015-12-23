#coding: utf-8
from __future__ import unicode_literals, absolute_import
import logging
import json

from wechatpy.replies import TextReply, TransferCustomerServiceReply

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
        if self.message.content.startswith('客服'):
            logger.info('Transfer to customer service')
            return TransferCustomerServiceReply(message=self.message).render()
        try:
            reminder = parse(self.message.content, uid=self.message.source)
            reminder.owner = self.user
            reminder.save()
            return self.text_reply(
                '/:ok将在%s提醒你%s\n\n内容: %s\n提醒时间: %s' % (
                    reminder.nature_time(), reminder.event or '',
                    reminder.desc, reminder.time.strftime('%Y/%m/%d %H:%M'))
            )
        except ValueError as e:
            return self.text_reply(unicode(e))
        except Exception as e:  # Catch all kinds of wired errors
            logger.exception('Semantic parse error')
            return self.handle_unknown()

    def handle_event_subscribe(self):
        return self.text_reply(
            'Dear %s，这是我刚注册的微信号，功能还在开发中，请先关注着，初步完成后，我会邀请你试用的，敬请期待哦~' % self.user.get_full_name()
        )

    def handle_unknown(self):
        return self.text_reply(
            'Hi %s! your %s message is\n%s' % (
                self.user.get_full_name(), self.message.type.lower(), self.json_msg)
        )

    def handle_event_unknown(self):
        return self.text_reply(
            'Hi %s! your %s event is\n%s' % (
                self.user.get_full_name(), self.message.event.lower(), self.json_msg)
        )

    def handle_voice(self):
        self.message.content = getattr(self.message, 'recognition', '') or ''
        return self.handle_text()
    #
    # def handle_image(self):
    #     return self.response_text('image\n' + self.json_msg)
    #
    # def handle_location(self):
    #     return self.response_text('location\n' + self.json_msg)
    #
    # def handle_shortvideo(self):
    #     return self.response_text('shortvideo\n' + self.json_msg)
    #
    # def handle_video(self):
    #     return self.response_text('video\n' + self.json_msg)


def handler_message(msg):
    # TODO unique based on msgid
    return WechatMessage(msg).handle()

