# coding: utf-8
from __future__ import unicode_literals, absolute_import
import os
import re
import logging
import jieba
import jieba.posseg as pseg
from dateutil.relativedelta import relativedelta
from django.utils import timezone
from remind.models import Remind
from .exceptions import ParseError

jieba.initialize()
logger = logging.getLogger(__name__)

CN_NUM = {
        u'〇': 0,
        u'一': 1,
        u'二': 2,
        u'三': 3,
        u'四': 4,
        u'五': 5,
        u'六': 6,
        u'七': 7,
        u'八': 8,
        u'九': 9,
         
        u'零': 0,
        u'壹': 1,
        u'贰': 2,
        u'叁': 3,
        u'肆': 4,
        u'伍': 5,
        u'陆': 6,
        u'柒': 7,
        u'捌': 8,
        u'玖': 9,
         
        u'貮': 2,
        u'两': 2,
    }
CN_UNIT = {
        u'十': 10,
        u'拾': 10,
        u'百': 100,
        u'佰': 100,
        u'千': 1000,
        u'仟': 1000,
        u'万': 10000,
        u'萬': 10000,
        u'亿': 100000000,
        u'億': 100000000,
        u'兆': 1000000000000,
    }


# 三百八十二 => 382
def parse_cn_number(cn_sentence):
    # First, convert different parts
    words_with_digit1 = [None]
    for word in cn_sentence:
        if word in CN_UNIT:
            unit = CN_UNIT[word]
            if isinstance(words_with_digit1[-1], int):
                words_with_digit1[-1] = words_with_digit1[-1] * unit
            elif unit == 10:
                words_with_digit1.append(10)
            else:
                words_with_digit1.append(word)
        elif word in CN_NUM:
            words_with_digit1.append(CN_NUM[word])
        else:
            words_with_digit1.append(word)

    # Second, merge
    words_with_digit2 = [None]
    for word in words_with_digit1[1:]:
        if isinstance(word, int) and isinstance(words_with_digit2[-1], int):
            words_with_digit2[-1] += word
        else:
            words_with_digit2.append(word)
    return ''.join(map(unicode, words_with_digit2[1:]))

for word in open(os.path.join(os.path.dirname(__file__), 'ignore_words.txt')):
    if word.strip():
        # Wait until #350 of jieba is fixed
        jieba.add_word(word.strip(), 1e-9)
jieba.add_word(u'下月', 9999)

DEFAULT_HOUR = 8
DEFAULT_MINUTE = 0


class LocalParser(object):

    afternoon = None
    do_what = ''
    words = []

    def __init__(self):
        self.idx = 0
        self.now = timezone.localtime(timezone.now())
        self.time_fields = {}
        self.time_delta_fields = {}
        self.repeat = [0]*Remind._meta.get_field('repeat').size

    def parse_by_rules(self, text):
        # TODO: refine me, here is an ad-hoc patch to distinguish weekday and hour
        _text = re.sub(ur'([周|星期]\w)(\d)', r'\1 \2', text, flags=re.U)
        self.words = pseg.lcut(parse_cn_number(_text), HMM=False)
        while self.has_next():
            beginning = self.get_index()

            self.consume_repeat()

            self.consume_year_period() \
                or self.consume_month_period() \
                or self.consume_day_period()

            self.consume_weekday_period() \
                or self.consume_hour_period() \
                or self.consume_minute_period() \
                or self.consume_second_period()

            self.consume_year() \
                or self.consume_month() \
                or self.consume_day()

            self.consume_hour()

            if self.get_index() != beginning:
                # Time found
                self.consume_word(u'准时')
                if self.consume_word(u'提醒'):
                    self.consume_word(u'我')
                if self.current_tag() == 'v' and self.peek_next_word() == u'我':
                    self.advance(2)
                self.consume_to_end()
                try:
                    self.now += relativedelta(**self.time_delta_fields)
                    self.now = self.now.replace(**self.time_fields)
                except ValueError:
                    raise ParseError(u'/:no亲，时间或者日期超范围了')
                # Donot set event to None, since serializer will just skip None and we will have no chance to modify it
                remind = Remind(time=self.now, repeat=self.repeat, desc=text, event=self.do_what)
                remind.reschedule()
                return remind
            else:
                self.advance()
        return None

    def consume_repeat(self):
        beginning = self.get_index()
        if self.consume_word(u'每', u'每隔'):
            self.consume_word(u'间隔')
            repeat_count = self.consume_digit()
            if repeat_count is None:
                repeat_count = 1
            if repeat_count > 100:
                raise ParseError(u'/:no亲，时间跨度太大哦~')
            self.consume_word(u'个')
            if self.consume_word(u'年') and self.consume_month():
                self.repeat[0] = repeat_count
                return self.get_index() - beginning
            elif self.consume_word(u'月') and self.consume_day():
                self.repeat[1] = repeat_count
                return self.get_index() - beginning
            elif self.consume_word(u'天'):
                # Set repeat first so it can be used in consume_hour()
                self.repeat[2] = repeat_count
                if not self.consume_hour():
                    self.time_fields['hour'] = DEFAULT_HOUR
                    self.time_fields['minute'] = DEFAULT_MINUTE
                return self.get_index() - beginning
            elif self.current_word() in (u'周', u'星期'):
                if self.peek_next_word() in (u'周', u'星期'):
                    self.consume_word(u'周', u'星期')
                if self.consume_weekday_period():
                    self.repeat[3] = repeat_count
                    return self.get_index() - beginning
            elif self.consume_word(u'小时'):
                self.consume_minute()
                raise ParseError(u'/:no亲，暂不支持小时级别的重复提醒哦~')
            elif self.consume_word(u'分', u'分钟'):
                # self.consume_minute()
                raise ParseError(u'/:no亲，暂不支持分钟级别的重复提醒哦~')
            elif self.consume_word(u'工作日'):
                raise ParseError(u'/:no亲，暂不支持工作日提醒哦，请换成每天试试~')
        self.set_index(beginning)
        return 0

    def consume_year(self):
        beginning = self.get_index()
        year = self.consume_digit()
        if year is None or not self.consume_word(u'年', '-'):
            self.set_index(beginning)
            return 0
        if year > 3000:
            raise ParseError(u'/:no亲，恕不能保证%s年的服务' % year)
        if self.consume_month():
            self.time_fields['year'] = year
            return self.get_index() - beginning
        return 0

    def consume_month(self):
        beginning = self.get_index()
        month = self.consume_digit()
        if month is None or not self.consume_word(u'月', '-', '/', '.'):
            self.set_index(beginning)
            return 0
        if month > 12:
            raise ParseError(u'/:no亲，一年哪有%s个月！' % month)
        if self.consume_day():
            self.time_fields['month'] = month
            return self.get_index() - beginning
        self.set_index(beginning)
        return 0

    def consume_day(self):
        beginning = self.get_index()
        day = self.consume_digit()
        if day is None or not self.consume_word(u'日', '号'):
            self.set_index(beginning)
            return 0
        if day > 31:
            raise ParseError(u'/:no亲，一个月哪有%s天！' % day)
        self.time_fields['day'] = day
        # 2016年12月14日周三在上海举办的2016 Google 开发者大会
        if self.consume_word(u'周', u'星期'):
            self.consume_word(u'日', u'天') or self.consume_digit()
        # set default time
        if not self.consume_hour():
            self.time_fields['hour'] = DEFAULT_HOUR
            self.time_fields['minute'] = DEFAULT_MINUTE
        return self.get_index() - beginning

    def consume_hour(self):
        beginning1 = self.get_index()
        if self.consume_word(u'早', u'早上', u'早晨', u'今早', u'上午'):
            self.afternoon = False
            self.time_fields['hour'] = DEFAULT_HOUR
            self.time_fields['minute'] = DEFAULT_MINUTE
        elif self.consume_word(u'中午'):
            self.afternoon = False
            self.time_fields['hour'] = 12
            self.time_fields['minute'] = DEFAULT_MINUTE
        elif self.consume_word(u'下午'):
            self.afternoon = True
            self.time_fields['hour'] = 13
            self.time_fields['minute'] = DEFAULT_MINUTE
        elif self.consume_word(u'傍晚'):
            self.afternoon = True
            self.time_fields['hour'] = 18
            self.time_fields['minute'] = DEFAULT_MINUTE
        elif self.consume_word(u'晚上', u'今晚'):
            self.afternoon = True
            self.time_fields['hour'] = 20
            self.time_fields['minute'] = DEFAULT_MINUTE

        beginning2 = self.get_index()
        hour = self.consume_digit()
        if hour is None or not self.consume_word(u'点', u'点钟', ':', u'：', u'.'):
            self.set_index(beginning2)
        else:
            if hour < 13:
                # if saying in the afternoon(should not equal to 12)
                if self.afternoon or (self.now.hour > 12 and not self.time_fields
                                      and not self.time_delta_fields and self.repeat == [0]*len(self.repeat)):
                    hour += 12
            if not (0 <= hour <= 24):
                raise ParseError(u'/:no亲，一天哪有%s小时！' % hour)
            self.time_fields['hour'] = hour
            if not self.consume_minute():
                self.time_fields['minute'] = DEFAULT_MINUTE
            return self.get_index() - beginning1
        return self.get_index() - beginning1

    # minute should only be called from hour
    def consume_minute(self):
        beginning = self.get_index()
        minute = self.consume_digit()
        if minute is not None:
            if not (0 <= minute <= 60):
                raise ParseError(u'/:no亲，一小时哪有%s分钟！' % minute)
            self.time_fields['minute'] = minute
            self.consume_word(u'分', u'分钟', ':')
            self.consume_second()
        elif self.consume_word('半'):
            self.time_fields['minute'] = 30
        elif self.current_word() == '1' and self.peek_next_word() == '刻':
            self.advance(2)
            self.time_fields['minute'] = 15
        elif self.current_word() == '3' and self.peek_next_word() == '刻':
            self.advance(2)
            self.time_fields['minute'] = 45
        return self.get_index() - beginning

    def consume_second(self):
        beginning = self.get_index()
        second = self.consume_digit()
        if second is not None:
            if self.consume_word(u'秒', u'秒钟'):
                if not (0 <= second <= 60):
                    raise ParseError(u'/:no亲，一分钟哪有%s秒！' % second)
                self.time_fields['second'] = second
                return self.get_index() - beginning
        self.set_index(beginning)
        return 0

    def consume_year_period(self):
        beginning = self.get_index()
        if self.consume_word(u'今年'):
            self.time_delta_fields['years'] = 0
        elif self.consume_word(u'明年'):
            self.time_delta_fields['years'] = 1
        elif self.consume_word(u'后年'):
            self.time_delta_fields['years'] = 2
        else:
            tmp = self.consume_digit()
            if tmp is not None and self.current_word() == u'年' and self.peek_next_word() in (u'后', u'以后'):
                self.time_delta_fields['years'] = tmp
                self.advance(2)
        if 'years' not in self.time_delta_fields:
            self.set_index(beginning)
            return 0
        self.consume_word(u'的')
        if self.time_delta_fields['years'] >= 100:
            raise ParseError(u'/:no亲，恕不能保证%s年后的服务啊！' % self.time_delta_fields['years'])
        self.consume_month()
        return self.get_index() - beginning

    def consume_month_period(self):
        beginning = self.get_index()
        if self.consume_word(u'下个月', u'下月'):
            self.time_delta_fields['months'] = 1
        elif self.current_word().isdigit():
            tmp = self.consume_digit()
            self.consume_word(u'个')
            if self.current_word() == u'月' and self.peek_next_word() in (u'后', u'以后'):
                self.time_delta_fields['months'] = tmp
                self.advance(2)
        if 'months' not in self.time_delta_fields:
            self.set_index(beginning)
            return 0
        self.consume_word(u'的')
        if self.time_delta_fields['months'] > 100:
            raise ParseError(u'/:no亲，%s个月跨度太大哦~' % self.time_delta_fields['months'])
        self.consume_day()  # 下个月五号
        return self.get_index() - beginning

    def consume_day_period(self):
        beginning = self.get_index()
        has_hour = False
        hour = DEFAULT_HOUR
        days = None
        if self.consume_word(u'今天'):
            days = 0
        elif self.consume_word(u'今早'):
            days = 0
            self.afternoon = False
        elif self.consume_word(u'今晚'):
            days = 0
            self.afternoon = True
            hour = 20
        elif self.consume_word(u'明天', u'明日'):
            days = 1
        elif self.consume_word(u'明早'):
            days = 1
            self.afternoon = False
        elif self.consume_word(u'明晚'):
            days = 1
            self.afternoon = True
            hour = 20
        elif self.consume_word(u'后天'):
            days = 2
        elif self.consume_word(u'大后天'):
            days = 3
        else:
            tmp = self.consume_digit()
            if tmp is not None and self.consume_word(u'天'):
                if self.consume_word(u'后', u'以后'):
                    days = tmp
                elif self.consume_hour_period():
                    days = tmp
                    has_hour = True
        if days is None:
            self.set_index(beginning)
            return 0
        if days > 1000:
            raise ParseError(u'/:no亲，%s天跨度太大哦~' % self.time_delta_fields['days'])
        self.time_delta_fields['days'] = days
        # 两天后下午三点
        if not has_hour and not self.consume_hour():
            self.time_fields['hour'] = hour
            self.time_fields['minute'] = DEFAULT_MINUTE
        return self.get_index() - beginning

    def consume_weekday_period(self):
        beginning = self.get_index()
        weekday = None
        week_delta = 0

        if self.consume_word(u'周', u'下周', u'下个周', u'星期', u'下星期', u'下个星期', u'礼拜', u'下礼拜', u'下个礼拜'):
            if self.consume_word(u'日', u'天'):
                weekday = 6
            elif self.consume_digit(False):
                weekday = self.consume_digit() - 1
                if not (0 <= weekday <= 5):
                    raise ParseError(u'/:no亲，一周哪有%s天！' % (weekday + 1))
                if self.now.weekday() == weekday:
                    week_delta = 1
        elif self.current_word().isdigit():
            tmp = self.consume_digit()
            self.consume_word(u'个')
            if self.current_word() in (u'周', u'星期', u'礼拜') and self.peek_next_word() in (u'后', u'以后'):
                week_delta = tmp
                self.advance(2)

        if weekday is not None:
            self.time_delta_fields['weekday'] = weekday
            self.time_delta_fields['days'] = 1
        elif week_delta != 0:
            if week_delta > 100:
                raise ParseError(u'/:no亲，%s星期跨度太大哦~' % week_delta)
            self.time_delta_fields['weeks'] = week_delta
        else:
            self.set_index(beginning)
            return 0

        if not self.consume_hour():
            self.time_fields['hour'] = DEFAULT_HOUR
            self.time_fields['minute'] = DEFAULT_MINUTE
        return self.get_index() - beginning

    def consume_hour_period(self):
        beginning = self.get_index()
        if self.current_word().isdigit():
            tmp = self.consume_digit()
            self.consume_word(u'个')
            if (self.consume_word(u'半小时') or (self.consume_word(u'半') and self.consume_word(u'钟头'))) \
                    and self.consume_word(u'后', u'以后'):
                self.time_delta_fields['hours'] = tmp
                self.time_delta_fields['minutes'] = 30
            elif self.consume_word(u'小时', u'钟头'):
                if self.consume_word(u'后', u'以后') or self.consume_minute_period():
                    self.time_delta_fields['hours'] = tmp
        elif self.consume_word(u'半小时') or (self.consume_word(u'半个') and self.consume_word(u'小时', u'钟头')):
            if self.consume_word(u'后', u'以后'):
                self.time_delta_fields['hours'] = 0
                self.time_delta_fields['minutes'] = 30
        if 'hours' not in self.time_delta_fields:
            self.set_index(beginning)
            return 0
        if self.time_delta_fields['hours'] > 100:
            raise ParseError(u'/:no亲，%s小时跨度太大哦~' % self.time_delta_fields['hours'])
        return self.get_index() - beginning

    def consume_minute_period(self):
        beginning = self.get_index()
        minute_delta = self.consume_digit()
        if minute_delta is not None:
            if self.consume_word(u'分', u'分钟'):
                self.consume_second_period()
                self.consume_word(u'后', u'以后')
                if minute_delta > 1000:
                    raise ParseError(u'/:no亲，%s分钟跨度太大哦~' % minute_delta)
                self.time_delta_fields['minutes'] = minute_delta
                return self.get_index() - beginning
        self.set_index(beginning)
        return 0

    def consume_second_period(self):
        beginning = self.get_index()
        second_delta = self.consume_digit()
        if second_delta is not None:
            if self.consume_word(u'秒', u'秒钟') and self.consume_word(u'后', u'以后'):
                if second_delta > 10000:
                    raise ParseError(u'/:no亲，%s秒跨度太大哦~' % second_delta)
                self.time_delta_fields['seconds'] = second_delta
                return self.get_index() - beginning
        self.set_index(beginning)
        return 0

    def consume_to_end(self):
        self.do_what = ''.join(map(lambda p: p.word, self.words[self.idx:]))
        return len(self.words) - self.idx

    def consume_word(self, *words):
        if self.current_word() in words:
            self.advance()
            return 1
        return 0

    def consume_phrase(self, *words):
        beginning = self.get_index()
        for word in words:
            if not self.consume_word(word):
                self.set_index(beginning)
                return 0
        return self.get_index() - beginning

    def consume_digit(self, consume=True):
        if self.current_word().isdigit():
            digit = int(self.current_word())
            if consume:
                self.advance()
            return digit
        return None

    def current_word(self):
        if self.idx >= len(self.words):
            return ''
        if self.words[self.idx].word.isspace() \
            or self.words[self.idx].word in [u'的', u'。', u'，', u'’', u'‘', u'！', u'？']:
            self.words.pop(self.idx)  # Do not advance, which will cause a consume
            return self.current_word()
        return self.words[self.idx].word

    def current_tag(self):
        if self.idx >= len(self.words):
            return ''
        if self.words[self.idx].word.isspace() or self.words[self.idx].word in (u'的',):
            self.words.pop(self.idx)
            return self.current_tag()
        return self.words[self.idx].flag

    def peek_next_word(self, step=1):
        beginning = self.get_index()
        word_list = []
        while step:
            step -= 1
            self.advance()
            word_list.append(self.current_word())
        self.set_index(beginning)
        return ''.join(word_list)

    def get_index(self):
        return self.idx

    def set_index(self, idx):
        self.idx = idx

    def has_next(self):
        return self.idx < len(self.words)

    def advance(self, step=1):
        self.idx += step

