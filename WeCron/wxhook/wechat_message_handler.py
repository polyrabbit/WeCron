#coding: utf-8
from __future__ import unicode_literals
import logging
import json

logger = logging.getLogger(__name__)

class WechatMessageHandler(object):

    def handle(self, wxmsg):
        logger.info('Get a %s from %s', wxmsg.type.lower(), wxmsg.source)
        handler = getattr(self, 'handle_%s' % wxmsg.type.lower(), self.handle_unknown)
        return handler(wxmsg)

    def handle_text(self, msg):
        return "I'm a text\n" + self.handle_unknown(msg)

    def handle_subscribe(self, msg):
        return 'Dear，这是我刚注册的微信号，功能还在开发中，请先关注着，初步完成后，我会邀请你试用的，敬请期待哦~\n\n' + \
            self.handle_unknown(msg)

    def handle_voice(self, msg):
        return 'voice\n' + self.handle_unknown(msg)

    def handle_image(self, msg):
        return 'image\n' + self.handle_unknown(msg)

    def handle_location(self, msg):
        return 'location\n' + self.handle_unknown(msg)

    def handle_shortvideo(self, msg):
        return 'shortvideo\n' + self.handle_unknown(msg)

    def handle_video(self, msg):
        return 'video\n' + self.handle_unknown(msg)

    def handle_unknown(self, msg):
        raw_attrs = msg.__dict__
        raw_attrs.pop('raw')
        return json.dumps(raw_attrs, ensure_ascii=False, indent=2)

wx_msg_handler = WechatMessageHandler()


def handle(msg):
    return wx_msg_handler.handle(msg)