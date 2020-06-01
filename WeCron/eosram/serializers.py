#coding: utf-8
from __future__ import unicode_literals, absolute_import
import logging

from rest_framework import serializers
from eosram.models import PriceThresholdChange, PricePercentageChange


logger = logging.getLogger(__name__)


class ThresholdSerializer(serializers.ModelSerializer):

    class Meta:
        model = PriceThresholdChange
        fields = ('id', 'threshold', 'increase', 'done', 'owner')


class PercentageSerializer(serializers.ModelSerializer):

    class Meta:
        model = PricePercentageChange
        fields = '__all__'
