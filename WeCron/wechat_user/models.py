#coding: utf-8
import logging
from datetime import datetime, timezone as dt_timezone
from zoneinfo import ZoneInfo, available_timezones

from django.db import models
from django.urls import reverse
from django.utils import timezone
from django.conf import settings
from django.contrib.auth.models import AbstractBaseUser, BaseUserManager

from requests import RequestException
from wechatpy.exceptions import WeChatClientException

from common import wechat_client
from remind.models import Remind

logger = logging.getLogger(__name__)
ALL_TIMEZONES = available_timezones()


class UserManager(BaseUserManager):

    def get_or_fetch(self, pk):
        u = self.filter(pk=pk).first()
        if u is None:
            return self.create(**self.amend_model_params(**wechat_client.user.get(pk)))
        if not u.unionid:
            # Mini program logins match users by it, e.g. users kept after unsubscribing may lack it
            try:
                u.unionid = wechat_client.user.get(pk).get('unionid')
            except (WeChatClientException, RequestException):
                logger.warning('Failed to fetch the UnionID of %s, retry on the next message', pk, exc_info=True)
            if u.unionid:
                u.save(update_fields=['unionid'])
        return u

    def amend_model_params(self, **kwargs):
        field_names = {f.name for f in WechatUser._meta.concrete_fields}
        params = {k: v for k, v in kwargs.items() if k in field_names and v != ''}
        if 'subscribe_time' in params:
            params['subscribe_time'] = datetime.fromtimestamp(params['subscribe_time'], dt_timezone.utc)
        params['subscribe'] = bool(params['subscribe'])
        return params

    def create_superuser(self, openid, password, **extra_fields):
        user = self.model(openid=openid, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    create_user = create_superuser


class WechatUser(AbstractBaseUser):
    openid = models.CharField(max_length=40, primary_key=True)
    unionid = models.CharField('UnionID', max_length=64, null=True, blank=True)
    subscribe = models.BooleanField('是否订阅', null=True, default=False,
                                    choices=((False, '未定阅'), (True, '已订阅'),))
    nickname = models.CharField('昵称', max_length=40, null=True)
    sex = models.SmallIntegerField('性别', null=True, choices=
            ((0, '未知'), (1, '男性'), (2, '女性'),))
    city = models.CharField('城市', max_length=100, null=True)
    country = models.CharField('国家', max_length=100, null=True)
    province = models.CharField('省份', max_length=100, null=True)
    language = models.CharField('语言', max_length=50, null=True)
    headimgurl = models.CharField('头像地址', max_length=200, null=True)
    subscribe_time = models.DateTimeField('关注时间', null=True)
    remark = models.CharField('备注', max_length=200, null=True)
    groupid = models.IntegerField('分组ID', null=True)
    morning_greeting = models.TimeField('早报时间', null=True, default='08:00')
    notify_subscription = models.BooleanField('提醒被订阅通知', null=True, default=True)
    timezone = models.CharField('默认时区', max_length=64, default=settings.TIME_ZONE)
    source = models.CharField('用户来源，区分从那个公众号关注过来', max_length=32, null=True)
    # WeChat only allows text messages within 48 hours since the user last messaged us
    last_message_time = models.DateTimeField('最后发消息时间', null=True, blank=True)
    last_login = None  # Drop the inherited field, web logins don't open the messaging window

    objects = UserManager()

    USERNAME_FIELD = 'openid'

    is_staff = True

    class Meta:
        ordering = ["-subscribe_time"]
        db_table = 'user'
        # unique=True would also create a LIKE index on PostgreSQL
        constraints = [models.UniqueConstraint(fields=['unionid'], name='user_unionid_uniq')]

    @property
    def id(self):
        return self.openid

    def __str__(self):
        return self.nickname

    def get_full_name(self):
        return self.nickname or ''  # avoid 'None', Wechat no longer sends nickname...

    get_short_name = get_full_name

    def get_absolute_url(self):
        return reverse('user_detail', args=(str(self.pk),))

    def get_time_reminds(self):
        created = self.time_reminds_created.all()
        participate = Remind.objects.filter(participants__contains=[self.pk])
        return (created | participate).order_by('time')

    def get_timezone(self):
        tzname = self.timezone
        if tzname not in ALL_TIMEZONES:
            tzname = settings.TIME_ZONE
        return ZoneInfo(tzname)

    def activate_timezone(self):
        timezone.activate(self.get_timezone())

    def unsubscribe(self):
        self.subscribe = False
        existing_count = self.time_reminds_created.count()
        if existing_count <= 100:
            self.time_reminds_created.all().delete()
            self.delete()
        else:
            self.save(update_fields=['subscribe'])

# A hack around django's not allowing override a parent model's attribute
WechatUser._meta.get_field('password').null = True

