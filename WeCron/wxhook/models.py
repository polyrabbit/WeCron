#coding: utf-8
from __future__ import unicode_literals, absolute_import
from datetime import datetime
import pytz

from django.db import models
from django.core.urlresolvers import reverse
from django.contrib.auth.models import AbstractBaseUser, BaseUserManager

from common import wechat_client
from remind.models import Remind


class UserManager(BaseUserManager):

    def get_or_fetch(self, pk):
        u = self.filter(pk=pk).first()
        if u:
            return u
        user_dict = wechat_client.user.get(pk)
        if 'subscribe_time' in user_dict:
            user_dict['subscribe_time'] = \
                datetime.fromtimestamp(user_dict['subscribe_time'], pytz.utc)
        return self.create(**user_dict)

    def create_superuser(self, openid, password, **extra_fields):
        user = self.model(openid=openid, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    create_user = create_superuser


class User(AbstractBaseUser):
    openid = models.CharField(max_length=40, primary_key=True)
    subscribe = models.NullBooleanField('是否订阅', default=True,
                                        choices=((0, '未定阅'), (1, '已订阅'),))
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

    objects = UserManager()

    USERNAME_FIELD = 'openid'

    is_staff = True

    class Meta:
        ordering = ["-subscribe_time"]
        db_table = 'user'

    @property
    def id(self):
        return self.openid

    def __unicode__(self):
        return self.nickname

    def get_full_name(self):
        return self.nickname

    get_short_name = get_full_name

    def get_absolute_url(self):
        return reverse('user_detail', args=(str(self.pk),))

    def get_time_reminds(self):
        created = self.time_reminds_created.all()
        participate = Remind.objects.filter(participants__contains=[self.pk])
        return (created | participate).order_by('time')

# A hack around django's not allowing override a parent model's attribute
User._meta.get_field('password').null = True
