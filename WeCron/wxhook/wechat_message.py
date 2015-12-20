#coding: utf-8
from __future__ import unicode_literals
import logging
import json

from wechatpy.replies import TextReply, TransferCustomerServiceReply

from .models import User

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
            content=reply_str,
            message=self.message,
        ).render()

    def handle(self):
        logger.info('Get a %s from %s', self.message.type.lower(), self.user.nickname)
        handler = getattr(self, 'handle_%s' % self.message.type.lower(), self.handle_unknown)
        return handler()

    def handle_text(self):
        if self.message.content.startswith('#'):
            logger.info('Transfer to customer service')
            return TransferCustomerServiceReply(message=self.message).render()
        return self.handle_unknown()

    def handle_subscribe(self):
        return self.text_reply(
            'Dear %s，这是我刚注册的微信号，功能还在开发中，请先关注着，初步完成后，我会邀请你试用的，敬请期待哦~' % self.user.nickname
        )

    def handle_unknown(self):
        return self.text_reply(
            'Hi %s! your %s message is\n%s' % (
                self.user.nickname, self.message.type.lower(), self.json_msg)
        )

    # def handle_voice(self):
    #     return self.response_text('voice\n' + self.json_msg)
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
    return WechatMessage(msg).handle()

