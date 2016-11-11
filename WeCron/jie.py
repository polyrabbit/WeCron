#coding: utf-8
from __future__ import unicode_literals, absolute_import
import logging
import re
import jieba
import jieba.posseg as pseg
import datetime
from django.utils import timezone

jieba.initialize()
logger = logging.getLogger(__name__)

CN_NUM = {
        u'〇' : 0,
        u'一' : 1,
        u'二' : 2,
        u'三' : 3,
        u'四' : 4,
        u'五' : 5,
        u'六' : 6,
        u'七' : 7,
        u'八' : 8,
        u'九' : 9,
         
        u'零' : 0,
        u'壹' : 1,
        u'贰' : 2,
        u'叁' : 3,
        u'肆' : 4,
        u'伍' : 5,
        u'陆' : 6,
        u'柒' : 7,
        u'捌' : 8,
        u'玖' : 9,
         
        u'貮' : 2,
        u'两' : 2,
    }
CN_UNIT = {
        u'十' : 10,
        u'拾' : 10,
        u'百' : 100,
        u'佰' : 100,
        u'千' : 1000,
        u'仟' : 1000,
        u'万' : 10000,
        u'萬' : 10000,
        u'亿' : 100000000,
        u'億' : 100000000,
        u'兆' : 1000000000000,
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

# jieba.suggest_freq(u'提醒我', True)


class LocalParser(object):

    idx = 0
    year = month = day = hour = minute = second = None
    delta = False
    do_what = ''

    def __init__(self):
        self.now = timezone.localtime(timezone.now())
        self.stashed_indexes = []

    def parse_by_rules(self, text):
        self.words = pseg.lcut(parse_cn_number(text))
        while self.has_next():
            if self.current_tag() == 'v':
                if self.current_word() == u'提醒':
                    self.advance()
                if self.current_word() == u'我':
                    self.advance()
                self.consume_to_end()
                if self.delta:
                    self.now += datetime.timedelta(days=365 * self.year + 30 * self.month + self.day,
                                                   hours=self.hour, minutes=self.minute)
                else:
                    if self.year:
                        self.now = self.now.replace(year=self.year)
                    if self.month:
                        self.now = self.now.replace(month=self.month)
                    if self.day:
                        self.now = self.now.replace(day=self.day)
                    if self.hour:
                        self.now = self.now.replace(hour=self.hour)
                    if self.minute:
                        self.now = self.now.replace(minute=self.minute)
                    if self.second:
                        self.now = self.now.replace(second=self.second)
                return self.now, self.do_what

            self.consume_year() \
            or self.consume_month() \
            or self.consume_day()

            self.consume_hour()

        last_word = ''
        while self.idx < len(self.words):
            word = self.words[self.idx]
            print word
            if word.isdigit():
                self.consume_year()

            if word == u'明天':
                now = self.now.replace(hour=8, minute=0)
                now += datetime.timedelta(day=1)
            elif word == u'后天':
                now = now.replace(hour=8, minute=0)
                now += datetime.timedelta(day=2)
            elif word == u'下午':
                afternoon = True
            elif word == u'后':
                delta = True
            if last_word.isdigit():
                last_word = int(last_word)
                if word == u'点':
                    now = now.replace(hour=last_word)
                elif word == u'小时':
                    hour = last_word
                elif word in (u'分', u'分钟'):
                    minute = last_word
                elif re.match(ur'(周|星期)(\d|日|天)', word):
                    to_weekday = re.match(ur'(周|星期)(\d|日|天)', word).group(2)

    def consume_year(self):
        self.stash()
        if not self.current_word().isdigit():
            self.pop_stash()
            return False
        year = int(self.current_word())
        self.advance()
        if self.current_word() not in (u'年', '-'):
            self.pop_stash()
            return False
        self.advance()
        if self.consume_month():
            self.year = year
            return True
        return False

    def consume_month(self):
        self.stash()
        if not self.current_word().isdigit():
            self.pop_stash()
            return False
        month = int(self.current_word())
        self.advance()
        if self.current_word() not in (u'月', '-'):
            self.pop_stash()
            return False
        self.advance()
        if self.consume_day():
            self.month = month
            return True
        return False

    def consume_day(self):
        self.stash()
        if not self.current_word().isdigit():
            self.pop_stash()
            return False
        day = int(self.current_word())
        self.advance()
        if self.current_word() not in (u'日', '号'):
            self.pop_stash()
            return False
        self.advance()
        self.day = day
        return True

    def consume_noon(self):
        self.stash()
        afternoon = self.current_word() == u'下午'
        if self.current_word() in (u'早上', u'早晨', u'上午', u'中午', u'下午'):
            self.advance()
        if self.consume_hour():
            return True

    def consume_hour(self):
        self.stash()
        if not self.current_word().isdigit():
            self.pop_stash()
            return False
        hour = int(self.current_word())
        self.advance()
        if self.current_word() not in (u'点', u'点钟', ':', u':'):
            self.pop_stash()
            return False
        self.advance()
        self.hour = hour
        self.consume_minute()
        return True

    # minute should be called from hour
    def consume_minute(self):
        if self.hour is None:  # hour must be set before
            return False
        self.stash()
        if self.current_word().isdigit():
            self.minute = int(self.current_word())
            if self.current_word() == u'分':
                self.advance()
        elif self.current_word() == '半':
            self.minute = 30
        elif self.current_word() == '1' and self.peek_next_word() == '刻':
            self.advance()
            self.minute = 15
        elif self.current_word() == '3' and self.peek_next_word() == '刻':
            self.advance()
            self.minute = 45
        self.advance()
        return True

    def consume_to_end(self):
        self.do_what = ''.join(map(lambda p: p.word, self.words[self.idx:])) or u'闹钟'
        return True

    def current_word(self):
        return self.words[self.idx].word

    def current_tag(self):
        return self.words[self.idx].flag

    def peek_next_word(self):
        if self.idx >= len(self.words):
            return None
        return self.words[self.idx+1].word

    def stash(self):
        self.stashed_indexes.append(self.idx)

    def pop_stash(self):
        self.idx = self.stashed_indexes.pop()

    def has_next(self):
        return self.idx < len(self.words)

    def advance(self):
        self.idx += 1

if __name__ == '__main__':
    import os
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "wecron.settings")

    test_dig = [u'九',
                u'十一',
                u'一百二十三',
                u'一千二百零三',
                u'一万一千一百零一',
                u'99八十一'
                ]
    for cn in test_dig:
        parse_cn_number(cn)

    cn_sentence = u"三点四十五分钟提醒我还二百三十四块钱"
    cn_sentence = u'10日上午八点半提醒我移动公司'
    cn_sentence = u'明天九点58提醒秒杀流量'
    cn_sentence = u'一分钟后提醒我'
    cn_sentence = u'早上十点提醒我发送牛轧糖'
    cn_sentence = u'周五下午提醒我发信息给花花'
    cn_sentence = u'2014年三月十五号提醒我吃饭'
    cn_sentence = u'2014年三月十五号叫醒我'
    cn_sentence = u'2014年三月十五号三点四十提醒我'
    print ','.join(map(unicode, LocalParser().parse_by_rules(cn_sentence)))
