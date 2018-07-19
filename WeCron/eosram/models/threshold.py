# coding: utf-8
from __future__ import unicode_literals
import uuid

from django.db import models
from django.conf import settings


class PriceThresholdChange(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4)

    done = models.BooleanField('已经提醒过', default=False)
    threshold = models.FloatField(null=True, db_index=True)
    increase = models.BooleanField('上涨还是下跌')
    owner = models.ForeignKey(settings.AUTH_USER_MODEL, verbose_name='创建者',
                              related_name='threshold_change', on_delete=models.CASCADE)

    class Meta:
        ordering = ["-threshold"]
        db_table = 'eosram_price_threshold_change'
