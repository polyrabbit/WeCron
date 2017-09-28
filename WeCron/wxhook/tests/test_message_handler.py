# coding: utf-8
from __future__ import unicode_literals, absolute_import

from django.test import TestCase
from django.db.models.signals import post_save
from django.utils import timezone
from wechatpy import parse_message
from httmock import urlmatch, response, HTTMock

from common import wechat_client
from common.tests import access_token_mock
from ..message_handler import handle_message
from wechat_user.models import WechatUser
from remind.models import Remind


@urlmatch(netloc=r'(.*\.)?api\.weixin\.qq\.com$', path='.*semantic')
def semantic_parser_mock(url, request):
    content = {
        "errcode": 0,
        "query": "提醒我明天上午十点开会",
        "semantic": {
            "details": {
                "answer": "",
                "context_info": {},
                "datetime": {
                    "date": '2999-11-13',
                    "date_lunar": "2015-11-13",
                    "time": "10:00:00",
                    "time_ori": "上午十点",
                    "type": "DT_ORI",
                    "week": "3"
                },
                "event": "开会",
                "hit_str": "提醒 我 明天 上午 十点 开会 ",
                "remind_type": "0"
            },
            "intent": "SEARCH"
        },
        "type": "remind"
    }
    headers = {
        'Content-Type': 'application/json'
    }
    return response(200, content, headers, request=request)


@urlmatch(netloc=r'(.*\.)?api\.weixin\.qq\.com$', path='/cgi-bin/message/custom/send')
def send_message_mock(url, request):
    content = {}
    headers = {
        'Content-Type': 'application/json'
    }
    return response(200, content, headers, request=request)


class MessageHandlerTestCase(TestCase):

    # Common strings
    remind_desc = '提醒我明天上午十点开会'
    instructions_to_use = '如需设置提醒'
    remind_base_on_location = '基于地理位置的提醒'

    mock = HTTMock(access_token_mock, semantic_parser_mock, send_message_mock)

    @classmethod
    def setUpTestData(cls):
        cls.mock.__enter__()

    def setUp(self):
        self.user = WechatUser(openid='FromUser', nickname='UserName')
        self.user.save()
        self.settings(WX_APPID='123').enable()
        wechat_client.appid = '123'
        # Disable scheduler
        post_save.disconnect(dispatch_uid='update-scheduler')

    def build_wechat_msg(self, req_text):
        return parse_message(req_text)

    def test_text(self):
        req_text = """
        <xml>
        <ToUserName><![CDATA[toUser]]></ToUserName>
        <FromUserName><![CDATA[FromUser]]></FromUserName>
        <CreateTime>1348831860</CreateTime>
        <MsgType><![CDATA[text]]></MsgType>
        <Content><![CDATA[%s]]></Content>
        <MsgId>1234567890123456</MsgId>
        </xml>
        """ % self.remind_desc
        wechat_msg = self.build_wechat_msg(req_text)
        resp_xml = handle_message(wechat_msg)
        self.assertIn('时间:', resp_xml)
        self.assertNotIn('重复:', resp_xml)

    def test_repeat_text(self):
        req_text = """
        <xml>
        <ToUserName><![CDATA[toUser]]></ToUserName>
        <FromUserName><![CDATA[FromUser]]></FromUserName>
        <CreateTime>1348831860</CreateTime>
        <MsgType><![CDATA[text]]></MsgType>
        <Content><![CDATA[%s]]></Content>
        <MsgId>1234567890123456</MsgId>
        </xml>
        """ % '每月20号提醒我还信用卡'
        wechat_msg = self.build_wechat_msg(req_text)
        resp_xml = handle_message(wechat_msg)
        self.assertIn('时间:', resp_xml)
        self.assertIn('重复:', resp_xml)
        self.assertIn('每月', resp_xml)

    def test_image(self):
        req_text = """
        <xml>
        <ToUserName><![CDATA[toUser]]></ToUserName>
        <FromUserName><![CDATA[FromUser]]></FromUserName>
        <CreateTime>1348831860</CreateTime>
        <MsgType><![CDATA[image]]></MsgType>
        <PicUrl><![CDATA[this is a url]]></PicUrl>
        <MediaId><![CDATA[media_id]]></MediaId>
        <MsgId>1234567890123456</MsgId>
        </xml>
        """
        wechat_msg = self.build_wechat_msg(req_text)
        resp_xml = handle_message(wechat_msg)
        self.assertIn(self.instructions_to_use, resp_xml)

    def test_voice(self):
        req_text = """
        <xml>
        <ToUserName><![CDATA[toUser]]></ToUserName>
        <FromUserName><![CDATA[FromUser]]></FromUserName>
        <CreateTime>1357290913</CreateTime>
        <MsgType><![CDATA[voice]]></MsgType>
        <MediaId><![CDATA[media_id]]></MediaId>
        <Format><![CDATA[Format]]></Format>
        <Recognition><![CDATA[%s]]></Recognition>
        <MsgId>1234567890123456</MsgId>
        </xml>
        """ % self.remind_desc
        wechat_msg = self.build_wechat_msg(req_text)
        resp_xml = handle_message(wechat_msg)
        self.assertIn('时间:', resp_xml)

    def test_voice_with_media_id(self):
        media_id = '1sew2_7_hbIOymbtyeZEoxaAnR83Hff0PM9b8ChEUmt5FRVA6-fHrmHdGre6iKGN'
        req_text = """
        <xml>
        <ToUserName><![CDATA[toUser]]></ToUserName>
        <FromUserName><![CDATA[FromUser]]></FromUserName>
        <CreateTime>1357290913</CreateTime>
        <MsgType><![CDATA[voice]]></MsgType>
        <MediaId><![CDATA[%s]]></MediaId>
        <Format><![CDATA[Format]]></Format>
        <Recognition><![CDATA[%s]]></Recognition>
        <MsgId>1234567890123456</MsgId>
        </xml>
        """ % (media_id, self.remind_desc)
        wechat_msg = self.build_wechat_msg(req_text)
        resp_xml = handle_message(wechat_msg)
        r = self.user.get_time_reminds().first()
        self.assertEqual(media_id, r.media_id)
        r.delete()

    def test_video(self):
        req_text = """
        <xml>
        <ToUserName><![CDATA[toUser]]></ToUserName>
        <FromUserName><![CDATA[FromUser]]></FromUserName>
        <CreateTime>1357290913</CreateTime>
        <MsgType><![CDATA[video]]></MsgType>
        <MediaId><![CDATA[media_id]]></MediaId>
        <ThumbMediaId><![CDATA[thumb_media_id]]></ThumbMediaId>
        <MsgId>1234567890123456</MsgId>
        </xml>
        """
        wechat_msg = self.build_wechat_msg(req_text)
        resp_xml = handle_message(wechat_msg)
        self.assertIn(self.instructions_to_use, resp_xml)

    def test_shortvideo(self):
        req_text = """
        <xml>
        <ToUserName><![CDATA[toUser]]></ToUserName>
        <FromUserName><![CDATA[FromUser]]></FromUserName>
        <CreateTime>1357290913</CreateTime>
        <MsgType><![CDATA[shortvideo]]></MsgType>
        <MediaId><![CDATA[media_id]]></MediaId>
        <ThumbMediaId><![CDATA[thumb_media_id]]></ThumbMediaId>
        <MsgId>1234567890123456</MsgId>
        </xml>
        """
        wechat_msg = self.build_wechat_msg(req_text)
        resp_xml = handle_message(wechat_msg)
        self.assertIn(self.instructions_to_use, resp_xml)

    def test_location(self):
        req_text = """
        <xml>
        <ToUserName><![CDATA[toUser]]></ToUserName>
        <FromUserName><![CDATA[FromUser]]></FromUserName>
        <CreateTime>1351776360</CreateTime>
        <MsgType><![CDATA[location]]></MsgType>
        <Location_X>23.134521</Location_X>
        <Location_Y>113.358803</Location_Y>
        <Scale>20</Scale>
        <Label><![CDATA[位置信息]]></Label>
        <MsgId>1234567890123456</MsgId>
        </xml>
        """
        wechat_msg = self.build_wechat_msg(req_text)
        resp_xml = handle_message(wechat_msg)
        self.assertIn(self.remind_base_on_location, resp_xml)

    def test_link(self):
        req_text = """
        <xml>
        <ToUserName><![CDATA[toUser]]></ToUserName>
        <FromUserName><![CDATA[FromUser]]></FromUserName>
        <CreateTime>1351776360</CreateTime>
        <MsgType><![CDATA[link]]></MsgType>
        <Title><![CDATA[公众平台官网链接]]></Title>
        <Description><![CDATA[公众平台官网链接]]></Description>
        <Url><![CDATA[url]]></Url>
        <MsgId>1234567890123456</MsgId>
        </xml>
        """
        wechat_msg = self.build_wechat_msg(req_text)
        resp_xml = handle_message(wechat_msg)
        self.assertIn(self.instructions_to_use, resp_xml)

    def test_subscribe_event(self):
        req_text = """
        <xml>
        <ToUserName><![CDATA[toUser]]></ToUserName>
        <FromUserName><![CDATA[FromUser]]></FromUserName>
        <CreateTime>123456789</CreateTime>
        <MsgType><![CDATA[event]]></MsgType>
        <Event><![CDATA[subscribe]]></Event>
        </xml>
        """
        wechat_msg = self.build_wechat_msg(req_text)
        resp_xml = handle_message(wechat_msg)
        self.assertIn('直接输入文字或者语音就可以快速创建提醒', resp_xml)
        self.user.refresh_from_db()
        self.assertTrue(self.user.subscribe)

    def test_subscribe_scan_event(self):
        req_text = """
        <xml>
        <ToUserName><![CDATA[toUser]]></ToUserName>
        <FromUserName><![CDATA[FromUser]]></FromUserName>
        <CreateTime>123456789</CreateTime>
        <MsgType><![CDATA[event]]></MsgType>
        <Event><![CDATA[subscribe]]></Event>
        <EventKey><![CDATA[qrscene_1832456703]]></EventKey>
        <Ticket><![CDATA[TICKET]]></Ticket>
        </xml>
        """
        wechat_msg = self.build_wechat_msg(req_text)
        resp_xml = handle_message(wechat_msg)
        self.assertNotIn('直接输入文字或者语音就可以快速创建提醒', resp_xml)
        self.user.refresh_from_db()
        self.assertTrue(self.user.subscribe)

    def test_unsubscribe_event(self):
        req_text = """
        <xml>
        <ToUserName><![CDATA[toUser]]></ToUserName>
        <FromUserName><![CDATA[FromUser]]></FromUserName>
        <CreateTime>123456789</CreateTime>
        <MsgType><![CDATA[event]]></MsgType>
        <Event><![CDATA[unsubscribe]]></Event>
        </xml>
        """
        wechat_msg = self.build_wechat_msg(req_text)
        resp_xml = handle_message(wechat_msg)
        # self.user.refresh_from_db()
        # self.assertFalse(self.user.subscribe)
        self.assertIsNone(WechatUser.objects.filter(pk=self.user.pk).first())

    def test_location_event(self):
        req_text = """
        <xml>
        <ToUserName><![CDATA[toUser]]></ToUserName>
        <FromUserName><![CDATA[FromUser]]></FromUserName>
        <CreateTime>123456789</CreateTime>
        <MsgType><![CDATA[event]]></MsgType>
        <Event><![CDATA[LOCATION]]></Event>
        <Latitude>23.137466</Latitude>
        <Longitude>113.352425</Longitude>
        <Precision>119.385040</Precision>
        </xml>
        """
        wechat_msg = self.build_wechat_msg(req_text)
        resp_xml = handle_message(wechat_msg)
        self.assertIn(self.remind_base_on_location, resp_xml)

    def test_click_event_for_remind_today(self):
        req_text = """
        <xml>
        <ToUserName><![CDATA[toUser]]></ToUserName>
        <FromUserName><![CDATA[FromUser]]></FromUserName>
        <CreateTime>123456789</CreateTime>
        <MsgType><![CDATA[event]]></MsgType>
        <Event><![CDATA[CLICK]]></Event>
        <EventKey><![CDATA[time_remind_today]]></EventKey>
        </xml>
        """
        wechat_msg = self.build_wechat_msg(req_text)
        resp_xml = handle_message(wechat_msg)
        self.assertIn('今天没有提醒', resp_xml)
        WechatUser(openid='abc', nickname='abc').save()
        r = Remind(time=timezone.now(), owner_id=self.user.pk, event='睡觉')
        r.save()
        resp_xml = handle_message(wechat_msg)
        self.assertIn(r.title(), resp_xml)
        self.assertIn(r.local_time_string('G:i'), resp_xml)

        r = Remind(time=timezone.now(), owner_id=self.user.pk, event='吃饭', participants=['abc'])
        r.save()
        self.assertEqual(WechatUser.objects.get(pk='abc').get_time_reminds().first(), r)

