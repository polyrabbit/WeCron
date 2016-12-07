#coding: utf-8
from __future__ import unicode_literals, absolute_import
import logging
from datetime import datetime
import uuid

from django.utils.dateformat import format
from django.contrib.auth import get_user_model
from rest_framework import serializers
from remind.models import Remind

# Convert uuid representation for a easier url catch
uuid.UUID.__str__ = uuid.UUID.get_hex


class TimestampField(serializers.DateTimeField):
    def to_representation(self, value):
        """ Return epoch time for a datetime object or ``None``"""
        try:
            return int(format(value, 'U'))*1000
        except (AttributeError, TypeError):
            return None

    def to_internal_value(self, value):
        return datetime.utcfromtimestamp(int(value)/1000.0)


class UserSerializer(serializers.ModelSerializer):

    class Meta:
        model = get_user_model()
        fields = ('nickname', 'headimgurl')


class RemindSerializer(serializers.ModelSerializer):
    # url = serializers.CharField(source='get_absolute_url', read_only=True)
    owner = UserSerializer(read_only=True)
    time = TimestampField()

    class Meta:
        model = Remind
        fields = ('title', 'time', 'owner', 'id', 'defer', 'desc')
