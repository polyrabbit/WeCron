# coding: utf-8
from __future__ import unicode_literals, absolute_import
import logging
import json
import os
import re

from datetime import timedelta
from django.utils import timezone
from django.contrib.auth import get_user_model
from wechatpy.replies import TextReply, TransferCustomerServiceReply, ImageReply
from wechatpy.exceptions import WeChatClientException
from shove import Shove
from pydub import AudioSegment

from common import wechat_client
from remind.models import Remind
from .todo_parser import parse, ParseError

logger = logging.getLogger(__name__)


class WechatMessage(object):

    def __init__(self, message):
        self.message = message
        self.user = get_user_model().objects.get_or_fetch(message.source)
        self.user.activate_timezone()

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
                    self.message.type, self.user.get_full_name())
        handler = getattr(self, 'handle_%s' % self.message.type.lower(), self.handle_unknown)
        return handler()

    def handle_event(self):
        handler = getattr(self, 'handle_%s_event' % self.message.event.lower(), self.handle_unknown_event)
        return handler()

    def handle_text(self, reminder=None):
        try:
            if not reminder:
                if re.search('(^eos\s*ram$)|(^ram$)', self.message.content, re.I):
                    return self.text_reply('EOS Ram价格提醒<a href="http://wecron.betacat.io/eosram/">请点击这里</a>')

                reminder = parse(self.message.content, uid=self.message.source)
                reminder.owner = self.user
                if hasattr(self.message, 'media_id'):
                    # This is a voice message
                    reminder.media_id = self.message.media_id
                reminder.save()
            reply_lines = [
                '/:ok将在%s提醒你%s' % (reminder.time_until(), reminder.event or ''),
                '\n备注: %s' % reminder.desc,
                '时间: %s' % reminder.local_time_string()
            ]
            if reminder.has_repeat():
                reply_lines.append('重复: %s' % reminder.get_repeat_text())
            # TODO: add \U0001F449 to the left of 修改
            reply_lines.append('\n<a href="%s">修改/分享</a>' % reminder.get_absolute_url(True))
            return self.text_reply('\n'.join(reply_lines))
        except ParseError as e:
            return self.text_reply(unicode(e))
        except (WeChatClientException, KeyError):  # TODO: refine it
            pass
        except Exception as e:  # Catch all kinds of wired errors
            logger.exception('Semantic parse error')
        if hasattr(self.message, 'media_id'):  # speech to text has a low recognition rate...
            return self.text_reply(
                '\U0001F648微信的语音转文字功能识别出来的是：\n\n“%s”\n\n'
                '是不是它又识别错了。。。要不直接发文字给我吧~' % self.message.content
            )
        return self.text_reply(
            '\U0001F648抱歉，我还只是一个比较初级的定时机器人，理解不了您刚才所说的话：\n\n“%s”\n\n'
            '或者您可以换个姿势告诉我该怎么定时，比如这样：\n\n'
            '“两个星期后提醒我去复诊”。\n'
            '“周五晚上提醒我打电话给老妈”。\n'
            '“每月20号提醒我还信用卡[捂脸]”。' % self.message.content
        )

    def welcome_text(self):
        return (
            '亲爱的 %s，恭喜您找到了一个好的时间管理工具！\n\n'
            '现在，直接输入文字或者语音就可以快速创建提醒啦~ 请点击下面的“使用方法”查看如何创建提醒。\n\n'
            '如果您觉得体验还不错，欢迎把微定时推荐给亲朋好友们，也欢迎大家的各种反馈\U0001F91D\n\n'
            'PS 这是一个开源项目，代码都在<a href="https://github.com/polyrabbit/WeCron">\U0001F449这里</a>，欢迎有开发技能的同学参与进来！'
            % self.user.get_full_name()
        )

    def handle_subscribe_event(self):
        self.user.subscribe = True
        self.user.save(update_fields=['subscribe'])
        return self.text_reply(self.welcome_text())

    def handle_subscribe_scan_event(self):
        if not self.user.subscribe:
            self.user.subscribe = True
            self.user.save(update_fields=['subscribe'])
            wechat_client.message.send_text(self.user.openid, self.welcome_text())
        if self.message.scene_id.isdigit():
            # legacy, when wechat doesn't support string as scene id
            subscribe_remind = Remind.objects.filter(
                id__gt='%s-0000-0000-0000-000000000000' % (hex(int(self.message.scene_id)).replace('0x', ''))
            ).order_by('id').first()
        elif self.message.scene_id == 'eos_ram_price':
            logger.info('Get an EOS ram price subscription from %s', self.user.get_full_name())
            return self.text_reply('亲爱的 %s，欢迎订阅EOS Ram价格变动提醒！\n\n'
                                   '点击<a href="http://wecron.betacat.io/eosram/">\U0001F449这里</a>'
                                   '设置你的提醒' % (self.user.get_full_name()))
        else:
            subscribe_remind = Remind.objects.filter(id=self.message.scene_id).first()
        if subscribe_remind:
            if subscribe_remind.add_participant(self.user.openid):
                logger.info('User(%s) participants a remind(%s)', self.user.get_full_name(), unicode(subscribe_remind))
            return self.handle_text(subscribe_remind)
        logger.warning('Cannot find remind from scene id %s', self.message.scene_id)
        return self.text_reply('处理不了的scene id呢: %s' % self.message.scene_id)

    handle_scan_event = handle_subscribe_scan_event

    def handle_unsubscribe_event(self):
        self.user.unsubscribe()
        return self.text_reply("Bye")

    def handle_unknown(self):
        return self.text_reply(
            '/:jj如需设置提醒，只需用语音或文字告诉我就行了，比如这样：\n\n'
            '“两个星期后提醒我去复诊”。\n'
            '“周五晚上提醒我打电话给老妈”。\n'
            '“每月20号提醒我还信用卡[捂脸]”。'
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
            self.message.content = speech_to_text(getattr(self.message, 'media_id', ''))
        if not self.message.content:
            logger.info('No "recognition" field for media_id "%s" and speech_to_text returns nothing', getattr(self.message, 'media_id', 'NOT_EXIST'))
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
            remind_text_list = self.format_remind_list(time_reminds)
            if remind_text_list:
                return self.text_reply('/:sunHi %s, 你今天的提醒有:\n\n%s' % (self.user.get_full_name(),
                                                                              '\n'.join(remind_text_list)))
            return self.text_reply('/:coffee今天没有提醒，休息一下吧！')
        elif self.message.key.lower() == 'time_remind_tomorrow':
            tomorrow = timezone.now() + timedelta(days=1)
            time_reminds = self.user.get_time_reminds().filter(time__date=tomorrow).order_by('time').all()
            remind_text_list = self.format_remind_list(time_reminds, True)
            if remind_text_list:
                return self.text_reply('/:sunHi %s, 你明天的提醒有:\n\n%s' % (self.user.get_full_name(),
                                                                              '\n'.join(remind_text_list)))
            return self.text_reply('/:coffee明天还没有提醒，休息一下吧！')
        elif self.message.key.lower() == 'customer_service':
            logger.info('Transfer to customer service for %s', self.user.get_full_name())
            return TransferCustomerServiceReply(message=self.message).render()
        elif self.message.key.lower() == 'join_group':
            logger.info('Sending 小密圈 QR code to %s', self.user.get_full_name())
            wechat_client.message.send_text(self.user.openid, u'喜欢微定时？请加入微定时小密圈，欢迎各种反馈和建议~')
            # http://mmbiz.qpic.cn/mmbiz_jpg/U4AEiaplkjQ3olQ6WLhRNIsLxb2LD4kdQSWN6PxulSiaY0dhwrY4HUVBBYFC8xawEd6Sf4ErGLk7EZTeD094ozxw/0?wx_fmt=jpeg
            return ImageReply(message=self.message, media_id='S8Jjk9aHXZ7wXSwK1qqu2UnkQSAHid-VQv_kxNUZnMI').render()
        elif self.message.key.lower() == 'donate':
            logger.info('Sending donation QR code to %s', self.user.get_full_name())
            wechat_client.message.send_text(self.user.openid, u'好的服务离不开大家的鼓励和支持，如果觉得微定时给你的生活带来了一丝便利，'
                                                              u'请使劲儿用赞赏来支持。')
            # http://mmbiz.qpic.cn/mmbiz_png/U4AEiaplkjQ2mLxVZTECsibyWGB2Jtxs1JRvLVuEmYuW8TWvjiawPicfllfMbCxbEkUaasffkREJuG6OB4czIKpqAA/0?wx_fmt=png
            return ImageReply(message=self.message, media_id='7S0601j-TRXg9wK_KVwWO6dYbJF01T3qAeY7LZmfvss').render()
        # elif self.message.key.lower() == 'donate_geizang': # geizang is dead
        #     logger.info('Sending donation GeiZang QR code to %s', self.user.get_full_name())
        #     wechat_client.message.send_text(self.user.openid, u'好的服务离不开大家的鼓励和支持，如果觉得微定时给你的生活带来了一丝便利，'
        #                                                       u'请使劲儿用赞赏来支持。')
        #     # http://mmbiz.qpic.cn/mmbiz_png/U4AEiaplkjQ0DypiahsELePfHTh2NysKvQmqTBoqVTHabpPPJiaqg5aFunCUdVwraGMdcCo2Tz9GngWccoch3YWow/0?wx_fmt=png
        #     return ImageReply(message=self.message, media_id='S8Jjk9aHXZ7wXSwK1qqu2d1M_OVm4CoEECgdDlrG0mQ').render()
        elif self.message.key.lower() == 'add_friend':
            logger.info('Sending personal QR code to %s', self.user.get_full_name())
            wechat_client.message.send_text(self.user.openid, u'长按下面的二维码，添加作者个人微信，等你来撩~')
            # http://mmbiz.qpic.cn/mmbiz_jpg/U4AEiaplkjQ1x2YoD9GRticXvMk5iaWJCtEVuChsHecnwdfHFbiafJarWXyiaABTu4pPUKibvnJ1ZGwUF7arzCaFkArw/0?wx_fmt=jpeg
            return ImageReply(message=self.message, media_id='7S0601j-TRXg9wK_KVwWOyIpME1FMy2eBhh6z8eyWrE').render()
        return self.handle_unknown_event()

    @staticmethod
    def format_remind_list(reminds, next_run_found=False):
        now = timezone.now()
        remind_text_list = []
        for rem in reminds:
            emoji = '\U0001F552'  # Clock
            # takewhile is too aggressive
            if rem.time < now:
                emoji = '\U00002713 '  # Done
            elif not next_run_found:
                next_run_found = True
                emoji = '\U0001F51C'  # Soon
            remind_text_list.append('%s %s - <a href="%s">%s</a>' %
                                    (emoji, rem.local_time_string('G:i'), rem.get_absolute_url(True), rem.title()))
        return remind_text_list


# shove = Shove('file:///tmp/wecron_last_msgid', sync=1)

def handle_message(msg):
    # msgid = str(msg.id)
    # if msgid not in ['0', 'None'] and shove.get('last_msgid') == msgid:  # Duplicated message
    #     return TextReply(
    #         content='',
    #         message=msg,
    #     ).render()
    # TODO unique based on msgid
    resp_msg = WechatMessage(msg).handle()
    # shove['last_msgid'] = msgid
    return resp_msg


def speech_to_text(media_id):
    if not media_id:
        return None
    media_url = wechat_client.media.get_url(media_id).replace('http://', 'https://')
    media_resp = wechat_client.get(media_url)
    if len(media_resp.content) == 0:
        logger.warn('Failed to download media id %s', media_id)
        return ''

    fname = 'audio.amr'
    d = media_resp.headers['content-disposition']
    matches = re.findall("filename=(.+)", d)
    if matches and len(matches) > 0:
        fname = matches[0].strip('"')
    fpath = '/tmp/' + fname
    with open(fpath, 'wb') as f:
        f.write(media_resp.content)

    try:
        audio = AudioSegment.from_file(fpath)
        out_file = audio.export(format='mp3')
        mp3_content = out_file.read()
        out_file.close()
    finally:
        os.remove(fpath)

    submit_url = 'https://api.weixin.qq.com/cgi-bin/media/voice/addvoicetorecofortext?access_token=%s&format=mp3&voice_id=%s' % (wechat_client.access_token, media_id)
    submit_json = wechat_client.post(submit_url, files={fname: mp3_content})
    if submit_json.get('errcode') != 0 and submit_json.get('errcode') != '0':
        logger.warn('Failed to submit media id %s: %s', media_id, submit_json)
        return ''

    text_url = 'https://api.weixin.qq.com/cgi-bin/media/voice/queryrecoresultfortext?access_token=%s&voice_id=%s&lang=zh_CN' % (wechat_client.access_token, media_id)
    text_json = wechat_client.post(text_url)
    logger.info('Speech to text result: "%s"', text_json.get('result'))
    return text_json.get('result')
