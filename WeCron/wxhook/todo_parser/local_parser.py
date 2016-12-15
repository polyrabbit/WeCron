#coding: utf-8
from __future__ import unicode_literals, absolute_import
import logging
import string
import jieba
import jieba.posseg as pseg
from dateutil.relativedelta import relativedelta
from django.utils import timezone
from remind.models import Remind

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

jieba.add_word(u'号叫', 1e-9) # Wait until #350 of jieba is fixed
jieba.add_word(u'星期日', 1e-9)
jieba.add_word(u'星期天', 1e-9)
jieba.add_word(u'周日', 1e-9)
jieba.add_word(u'周天', 1e-9)
jieba.add_word(u'礼拜日', 1e-9)
jieba.add_word(u'礼拜天', 1e-9)
jieba.add_word(u'今天下午', 1e-9)
jieba.add_word(u'下月', 9999)

DEFAULT_HOUR = 8
DEFAULT_MINUTE = 0


class LocalParser(object):

    year = month = day = hour = minute = second = afternoon = None
    do_what = None
    words = []

    def __init__(self):
        self.idx = 0
        self.now = timezone.localtime(timezone.now())

    def parse_by_rules(self, text):
        self.words = pseg.lcut(parse_cn_number(text), HMM=False)
        while self.has_next():
            beginning = self.get_index()

            self.consume_year_period() \
                or self.consume_month_period() \
                or self.consume_day_period()

            self.consume_weekday_period() \
                or self.consume_hour_period() \
                or self.consume_minute_period()

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
                return Remind(time=self.now, desc=text, event=self.do_what)
            else:
                self.advance()
        return None

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

    def consume_year(self):
        beginning = self.get_index()
        year = self.consume_digit()
        if year is None or not self.consume_word(u'年', '-'):
            self.set_index(beginning)
            return 0
        if self.consume_month():
            self.now = self.now.replace(year=year)
            return self.get_index() - beginning
        return 0

    def consume_month(self):
        beginning = self.get_index()
        month = self.consume_digit()
        if month is None or not self.consume_word(u'月', '-', '/', '.'):
            self.set_index(beginning)
            return 0
        if self.consume_day():
            self.now = self.now.replace(month=month)
            return self.get_index() - beginning
        return 0

    def consume_day(self):
        beginning = self.get_index()
        day = self.consume_digit()
        if day is None or not self.consume_word(u'日', '号'):
            self.set_index(beginning)
            return 0
        self.now = self.now.replace(day=day)
        if not self.consume_hour():
            self.now = self.now.replace(hour=DEFAULT_HOUR, minute=DEFAULT_MINUTE)
        return self.get_index() - beginning

    def consume_hour(self):
        beginning1 = self.get_index()
        if self.consume_word(u'早', u'早上', u'早晨', u'今早', u'上午'):
            self.afternoon = False
            self.now = self.now.replace(hour=DEFAULT_HOUR, minute=DEFAULT_MINUTE)
        elif self.consume_word(u'中午'):
            self.afternoon = False
            self.now = self.now.replace(hour=12, minute=DEFAULT_MINUTE)
        elif self.consume_word(u'下午'):
            self.afternoon = True
            self.now = self.now.replace(hour=13, minute=DEFAULT_MINUTE)
        elif self.consume_word(u'傍晚'):
            self.afternoon = True
            self.now = self.now.replace(hour=18, minute=DEFAULT_MINUTE)
        elif self.consume_word(u'晚上', u'今晚'):
            self.afternoon = True
            self.now = self.now.replace(hour=20, minute=DEFAULT_MINUTE)

        beginning2 = self.get_index()
        hour = self.consume_digit()
        if hour is None or not self.consume_word(u'点', u'点钟', ':', u':'):
            self.set_index(beginning2)
        else:
            if self.afternoon and hour < 13:
                hour += 12
            if hour > 24:
                self.set_index(beginning2)
            else:
                self.now = self.now.replace(hour=hour)
                if not self.consume_minute():
                    self.now = self.now.replace(minute=DEFAULT_MINUTE)
                return self.get_index() - beginning1

        return self.get_index() - beginning1

    # minute should only be called from hour
    def consume_minute(self):
        beginning = self.get_index()
        minute = self.consume_digit()
        if minute is not None:
            self.now = self.now.replace(minute=minute)
            self.consume_word(u'分', u'分钟', ':')
        elif self.consume_word('半'):
            self.now = self.now.replace(minute=30)
        elif self.current_word() == '1' and self.peek_next_word() == '刻':
            self.advance(2)
            self.now = self.now.replace(minute=15)
        elif self.current_word() == '3' and self.peek_next_word() == '刻':
            self.advance(2)
            self.now = self.now.replace(minute=45)
        return self.get_index() - beginning

    def consume_year_period(self):
        beginning = self.get_index()
        year_delta = None
        if self.consume_word(u'明年'):
            year_delta = 1
        elif self.consume_word(u'后年'):
            year_delta = 2
        else:
            tmp = self.consume_digit()
            if tmp is not None and self.current_word() == u'年' and self.peek_next_word() in (u'后', u'以后'):
                year_delta = tmp
                self.advance(2)
        if year_delta is None:
            self.set_index(beginning)
            return 0
        self.consume_word(u'的')
        self.now += relativedelta(years=year_delta)
        self.consume_month()
        return self.get_index() - beginning

    def consume_month_period(self):
        beginning = self.get_index()
        month_delta = None
        if self.consume_word(u'下个月', u'下月'):
            month_delta = 1
        elif self.current_word().isdigit():
            tmp = self.consume_digit()
            self.consume_word(u'个')
            if self.current_word() == u'月' and self.peek_next_word() in (u'后', u'以后'):
                month_delta = tmp
                self.advance(2)
        if month_delta is None:
            self.set_index(beginning)
            return 0
        self.consume_word(u'的')
        self.now += relativedelta(months=month_delta)
        self.consume_day()  # 下个月五号
        return self.get_index() - beginning

    def consume_day_period(self):
        beginning = self.get_index()
        day_delta = None
        has_hour = False
        if self.consume_word(u'今天'):
            day_delta = 0
        elif self.consume_word(u'今早'):
            day_delta = 0
            self.afternoon = False
        elif self.consume_word(u'今晚'):
            day_delta = 0
            self.afternoon = True
        elif self.consume_word(u'明天'):
            day_delta = 1
        elif self.consume_word(u'明早'):
            day_delta = 1
            self.afternoon = False
        elif self.consume_word(u'明晚'):
            day_delta = 1
            self.afternoon = True
        elif self.consume_word(u'后天'):
            day_delta = 2
        elif self.consume_word(u'大后天'):
            day_delta = 3
        else:
            tmp = self.consume_digit()
            if tmp is not None and self.consume_word(u'天'):
                if self.consume_word(u'后', u'以后'):
                    day_delta = tmp
                elif self.consume_hour_period():
                    day_delta = tmp
                    has_hour = True
        if day_delta is None:
            self.set_index(beginning)
            return 0
        self.now += relativedelta(days=day_delta)
        # 两天后下午三点
        if not has_hour and not self.consume_hour():
            self.now = self.now.replace(hour=DEFAULT_HOUR, minute=DEFAULT_MINUTE)
        return self.get_index() - beginning

    def consume_weekday_period(self):
        beginning = self.get_index()
        weekday = None
        week_delta = 0

        if self.consume_word(u'周', u'下周', u'星期', u'下星期', u'礼拜', u'下礼拜'):
            if self.consume_word(u'日', u'天'):
                weekday = 6
            elif self.consume_digit(False):
                weekday = self.consume_digit() - 1
                if not (0 <= weekday <= 5):
                    weekday = None
        elif self.current_word().isdigit():
            tmp = self.consume_digit()
            self.consume_word(u'个')
            if self.current_word() in (u'周', u'星期', u'礼拜') and self.peek_next_word() in (u'后', u'以后'):
                week_delta = tmp
                self.advance(2)

        if weekday is not None or week_delta != 0:
            self.now += relativedelta(weekday=weekday, weeks=week_delta)
            if not self.consume_hour():
                self.now = self.now.replace(hour=DEFAULT_HOUR, minute=DEFAULT_MINUTE)
            return self.get_index() - beginning
        self.set_index(beginning)
        return 0

    def consume_hour_period(self):
        beginning = self.get_index()
        hour_delta = None
        minutes_delta = 0
        if self.current_word().isdigit():
            tmp = self.consume_digit()
            self.consume_word(u'个')
            if (self.consume_word(u'半小时') or (self.consume_word(u'半') and self.consume_word(u'钟头'))) \
                    and self.consume_word(u'后', u'以后'):
                hour_delta = tmp
                minutes_delta = 30
            elif self.consume_word(u'小时', u'钟头'):
                if self.consume_word(u'后', u'以后') or self.consume_minute_period():
                    hour_delta = tmp
        elif self.consume_word(u'半小时') or (self.consume_word(u'半个') and self.consume_word(u'小时', u'钟头')):
            if self.consume_word(u'后', u'以后'):
                hour_delta = 0
                minutes_delta = 30
        if hour_delta is None:
            self.set_index(beginning)
            return 0
        self.now += relativedelta(hours=hour_delta, minutes=minutes_delta)
        return self.get_index() - beginning

    def consume_minute_period(self):
        beginning = self.get_index()
        minute_delta = self.consume_digit()
        if minute_delta is not None:
            if self.consume_word(u'分', u'分钟'):
                self.consume_word(u'后', u'以后')
                self.now += relativedelta(minutes=minute_delta)
                return self.get_index() - beginning
        self.set_index(beginning)
        return 0

    def consume_to_end(self):
        self.do_what = ''.join(map(lambda p: p.word, self.words[self.idx:])) or None
        return len(self.words) - self.idx

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
        if self.idx+step >= len(self.words):
            return None
        return ''.join(map(lambda seg: seg.word, self.words[self.idx+1:self.idx+step+1]))

    def get_index(self):
        return self.idx

    def set_index(self, idx):
        self.idx = idx

    def has_next(self):
        return self.idx < len(self.words)

    def advance(self, step=1):
        self.idx += step

