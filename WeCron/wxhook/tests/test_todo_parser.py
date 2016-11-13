# coding: utf-8
from __future__ import unicode_literals, absolute_import
from dateutil.relativedelta import relativedelta
from django.utils import timezone
from django.test import TestCase

from ..todo_parser.local_parser import LocalParser, parse_cn_number, DEFAULT_HOUR


class ViewsTestCase(TestCase):

    def setUp(self):
        self.now = timezone.localtime(timezone.now())
        self.parse = LocalParser().parse_by_rules

    def test_cn_parser(self):
        test_dig = [u'九',
                    u'十一',
                    u'一百二十三',
                    u'一千二百零三',
                    u'一万一千一百零一',
                    u'99八十一'
                    ]

        result_dig = []
        for cn in test_dig:
            result_dig.append(parse_cn_number(cn))
        self.assertListEqual(result_dig, ['9', '11', '123', '1203', '11101', '9981'])

    def test_parse_failed(self):
        text = '哈哈哈哈哈哈'
        reminder = self.parse(text)
        self.assertIsNone(reminder)

    def test_parse_year(self):
        text = '吃吃吃2016年三月十五号下午三点四十提醒我睡觉'
        reminder = self.parse(text)
        self.assertEqual(reminder.desc, text)
        self.assertEqual(reminder.title(), '睡觉')
        self.assertEquals(reminder.time.year, 2016)
        self.assertEquals(reminder.time.month, 3)
        self.assertEquals(reminder.time.day, 15)
        self.assertEquals(reminder.time.hour, 15)
        self.assertEquals(reminder.time.minute, 40)

    def test_parse_hour(self):
        text = '三点四十五分钟提醒我还二百三十四块钱'
        reminder = self.parse(text)
        self.assertEqual(reminder.desc, text)
        self.assertEqual(reminder.title(), '还234块钱')
        self.assertEquals(reminder.time.hour, 3)
        self.assertEquals(reminder.time.minute, 45)

    def test_parse_hour_with_morning(self):
        text = '早上十点提醒我发送牛轧糖'
        reminder = self.parse(text)
        self.assertEqual(reminder.desc, text)
        self.assertEqual(reminder.title(), '发送牛轧糖')
        self.assertEquals(reminder.time.hour, 10)
        self.assertEquals(reminder.time.minute, 0)

    def test_parse_hour_with_night(self):
        text = '今天晚上二十二点提醒我拿快递'
        reminder = self.parse(text)
        self.assertEqual(reminder.desc, text)
        self.assertEqual(reminder.title(), '拿快递')
        self.assertEquals(reminder.time.hour, 22)
        self.assertEquals(reminder.time.minute, 0)

    def test_parse_hour_with_night2(self):
        # 也测试分词
        text = '今晚八点半导体制冷片'
        reminder = self.parse(text)
        self.assertEqual(reminder.desc, text)
        self.assertEqual(reminder.title(), '半导体制冷片')
        self.assertEquals(reminder.time.hour, 20)
        self.assertEquals(reminder.time.minute, 0)

    def test_parse_half_day(self):
        text = '10日下午八点半提醒我移动公司'
        reminder = self.parse(text)
        self.assertEqual(reminder.desc, text)
        self.assertEqual(reminder.title(), '移动公司')
        self.assertEqual(reminder.time.day, 10)
        self.assertEquals(reminder.time.hour, 20)
        self.assertEquals(reminder.time.minute, 30)

    def test_parse_minute_period(self):
        text = '一分钟后提醒我'
        reminder = self.parse(text)
        self.assertEqual(reminder.desc, text)
        self.assertEqual(reminder.title(), '闹钟')
        self.assertEqual(reminder.time_until(), '1分钟后')
        self.assertAlmostEqual((reminder.time - self.now).seconds, 60, delta=2)

    def test_parse_hour_period_with_minute(self):
        # 分后 is required here, for when HMM is True, "分后" will become a word
        text = '一小时三十分后提醒我'
        reminder = self.parse(text)
        self.assertEqual(reminder.desc, text)
        self.assertEqual(reminder.title(), '闹钟')
        self.assertAlmostEqual((reminder.time - self.now).seconds, 90 * 60, delta=2)

    def test_parse_hour_period_with_half(self):
        text = '两个半小时后提醒我'
        reminder = self.parse(text)
        self.assertEqual(reminder.desc, text)
        self.assertEqual(reminder.title(), '闹钟')
        self.assertAlmostEqual((reminder.time - self.now).seconds, 150 * 60, delta=2)

    def test_parse_hour_period_with_only_half(self):
        text = '半小时后提醒我同步'
        reminder = self.parse(text)
        self.assertEqual(reminder.desc, text)
        self.assertEqual(reminder.title(), '同步')
        self.assertAlmostEqual((reminder.time - self.now).seconds, 30 * 60, delta=2)
        self.setUp()
        text = '半个钟头后提醒我同步'
        reminder = self.parse(text)
        self.assertEqual(reminder.desc, text)
        self.assertEqual(reminder.title(), '同步')
        self.assertAlmostEqual((reminder.time - self.now).seconds, 30 * 60, delta=2)

    def test_parse_day_period(self):
        text = '明天九点58提醒秒杀流量'
        reminder = self.parse(text)
        self.assertEqual(reminder.desc, text)
        self.assertEqual(reminder.title(), '秒杀流量')
        self.assertEqual(reminder.time.day-self.now.day, 1)
        self.assertEquals(reminder.time.hour, 9)
        self.assertEquals(reminder.time.minute, 58)

    def test_parse_day_period_with_half(self):
        text = '明晚八点去看电影'
        reminder = self.parse(text)
        self.assertEqual(reminder.desc, text)
        self.assertEqual(reminder.title(), '去看电影')
        self.assertEqual(reminder.time.day-self.now.day, 1)
        self.assertEquals(reminder.time.hour, 20)
        self.assertEquals(reminder.time.minute, 0)
        self.setUp()
        reminder = self.parse(u'今晚八点去看电影')
        self.assertEqual(reminder.time.day - self.now.day, 0)
        self.assertEquals(reminder.time.hour, 20)
        self.assertEquals(reminder.time.minute, 0)

    def test_parse_with_punctuation_in_time(self):
        text = '明天09:30提醒我把门的报告递交上去'
        reminder = self.parse(text)
        self.assertEqual(reminder.desc, text)
        self.assertEqual(reminder.title(), '把门的报告递交上去')
        self.assertEqual(reminder.time.day - self.now.day, 1)
        self.assertEquals(reminder.time.hour, 9)
        self.assertEquals(reminder.time.minute, 30)

    def test_parse_day_period_without_hour(self):
        text = '九十九天后秒杀流量'
        reminder = self.parse(text)
        self.assertEqual(reminder.desc, text)
        self.assertEqual(reminder.title(), '秒杀流量')
        self.assertAlmostEqual((reminder.time - self.now).days, 99, delta=1)
        self.assertEquals(reminder.time.hour, DEFAULT_HOUR)
        self.assertEquals(reminder.time.minute, 0)

    def test_parse_weekday(self):
        text = '周五下午提醒我发信息给花花'
        reminder = self.parse(text)
        self.assertEqual(reminder.desc, text)
        self.assertEqual(reminder.title(), '发信息给花花')
        self.assertEqual(reminder.time.isoweekday(), 5)
        self.assertEquals(reminder.time.hour, 13)
        self.assertEquals(reminder.time.minute, 0)

    def test_parse_weekday_period(self):
        text = '两个星期后下午提醒我发信息给花花'
        reminder = self.parse(text)
        self.assertEqual(reminder.desc, text)
        self.assertEqual(reminder.title(), '发信息给花花')
        self.assertAlmostEqual((reminder.time - self.now).days, 14, delta=1)
        self.assertEquals(reminder.time.hour, 13)
        self.assertEquals(reminder.time.minute, 0)

    def test_parse_weekday_period_with_wrong_segmentation(self):
        for word in [u'礼拜天', u'周日', u'周天']:
            self.setUp()
            text = word + u'晚上八点半提醒我找入团申请'
            reminder = self.parse(text)
            self.assertEquals(reminder.desc, text)
            self.assertEquals(reminder.title(), '找入团申请')
            self.assertEquals(reminder.time.isoweekday(), 7)
            self.assertEquals(reminder.time.hour, 20)
            self.assertEquals(reminder.time.minute, 30)

    def test_parse_month_period(self):
        text = '三个月后的早上提醒我写代码'
        reminder = self.parse(text)
        self.assertEqual(reminder.desc, text)
        self.assertEqual(reminder.title(), '写代码')
        self.assertAlmostEqual((reminder.time - self.now).days, 90, delta=2)
        self.assertEqual(reminder.time.day, self.now.day)
        self.assertEquals(reminder.time.hour, DEFAULT_HOUR)
        self.assertEquals(reminder.time.minute, 0)

    def test_parse_month_period_with_day(self):
        text = '下个月三号早上写代码'
        reminder = self.parse(text)
        self.assertEqual(reminder.desc, text)
        self.assertEqual(reminder.title(), '写代码')
        self.assertEqual((self.now + relativedelta(months=1)).month, reminder.time.month)
        self.assertEqual(reminder.time.day, 3)
        self.assertEquals(reminder.time.hour, DEFAULT_HOUR)
        self.assertEquals(reminder.time.minute, 0)

    def test_parse_year_period_with_day(self):
        text = '明年五月十五号叫我起床'
        reminder = self.parse(text)
        self.assertEqual(reminder.desc, text)
        self.assertEqual(reminder.title(), '起床')
        self.assertEqual((self.now + relativedelta(years=1)).year, reminder.time.year)
        self.assertEqual(reminder.time.month, 5)
        self.assertEqual(reminder.time.day, 15)
        self.assertEquals(reminder.time.hour, DEFAULT_HOUR)
        self.assertEquals(reminder.time.minute, 0)

    def test_parse_word_segmentation(self):
        text = '下月5号提醒杨二所还1600，刀正英1900'
        reminder = self.parse(text)
        self.assertEqual(reminder.desc, text)
        self.assertEqual(reminder.title(), '杨2所还1600，刀正英1900')
        self.assertEqual((self.now + relativedelta(months=1)).month, reminder.time.month)
        self.assertEqual(reminder.time.day, 5)
        self.assertEquals(reminder.time.hour, DEFAULT_HOUR)
        self.assertEquals(reminder.time.minute, 0)

    def test_parse_with_stop_words(self):
        text = '11月19号 的8点？，。  的   团费'
        reminder = self.parse(text)
        self.assertEqual(reminder.desc, text)
        self.assertEqual(reminder.title(), '团费')
        self.assertEqual(reminder.time.month, 11)
        self.assertEqual(reminder.time.day, 19)
        self.assertEquals(reminder.time.hour, 8)
        self.assertEquals(reminder.time.minute, 0)
