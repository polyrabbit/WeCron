#coding: utf-8
from __future__ import unicode_literals
import logging
import json

from django.conf import settings
from wechat_sdk import WechatBasic
from wechat_sdk.reply import WechatReply

logger = logging.getLogger(__name__)


class WechatClient(WechatBasic):

    def __init__(self):
        super(WechatClient, self).__init__(
                token=settings.WX_SIGN_TOKEN,
            )

    @property
    def json_msg(self):
        raw_attrs = self.message.__dict__
        raw_attrs.pop('raw')
        return json.dumps(raw_attrs, ensure_ascii=False, indent=2)

    def parse_message(self, raw_msg):
        self.parse_data(raw_msg)  # Raises exception on error
        logger.info('Get a %s from %s', self.message.type.lower(), self.message.source)
        handler = getattr(self, 'handle_%s' % self.message.type.lower(), self.handle_unknown)
        return handler()

    def handle_text(self):
        if self.message.content.startswith('#'):
            logger.info('Transfer to customer service')
            return GroupTransferReply(message=self.message).render()
        return self.response_text("I'm a text\n" + self.json_msg)

    def handle_subscribe(self):
        return self.response_text('Dear，这是我刚注册的微信号，功能还在开发中，请先关注着，初步完成后，我会邀请你试用的，敬请期待哦~\n\n' + self.json_msg)

    def handle_voice(self):
        return self.response_text('voice\n' + self.json_msg)

    def handle_image(self):
        return self.response_text('image\n' + self.json_msg)

    def handle_location(self):
        return self.response_text('location\n' + self.json_msg)

    def handle_shortvideo(self):
        return self.response_text('shortvideo\n' + self.json_msg)

    def handle_video(self):
        return self.response_text('video\n' + self.json_msg)

    def handle_unknown(self):
        return self.response_text(self.message.type.lower() + '\n' + self.json_msg)


# Will wait until PR 37 get merged
class GroupTransferReply(WechatReply):
    """
    客服群发转发消息
    """
    TEMPLATE = u"""
    <xml>
    <ToUserName><![CDATA[{target}]]></ToUserName>
    <FromUserName><![CDATA[{source}]]></FromUserName>
    <CreateTime>{time}</CreateTime>
    <MsgType><![CDATA[transfer_customer_service]]></MsgType>
    </xml>
    """

    def __init__(self, message):
        """
        :param message: WechatMessage 对象
        """
        super(GroupTransferReply, self).__init__(message=message)

    def render(self):
        return GroupTransferReply.TEMPLATE.format(**self._args)
