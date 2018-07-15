# coding: utf-8
from __future__ import unicode_literals
import uuid

from django.utils.timezone import now
from django.db import models


class PriceHistory(models.Model):

    time = models.DateTimeField('时间', db_index=True, default=now)
    price = models.FloatField()

    class Meta:
        ordering = ["time"]
        db_table = 'eosram_price_history'
