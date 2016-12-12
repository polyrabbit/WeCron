#coding: utf-8
from __future__ import unicode_literals, absolute_import
import logging
from datetime import datetime
import uuid

from django.utils.dateformat import format
from django.contrib.auth import get_user_model
from django.utils.timezone import utc
from rest_framework import serializers
from rest_framework.exceptions import ValidationError, PermissionDenied
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
        try:
            return datetime.fromtimestamp(int(value)/1000.0, utc)
        except ValueError:
            raise ValidationError('Invalid format')


class UserSerializer(serializers.ModelSerializer):
    id = serializers.CharField(source='openid', read_only=True)

    class Meta:
        model = get_user_model()
        fields = ('nickname', 'headimgurl', 'id')


class RemindSerializer(serializers.ModelSerializer):
    # apiEndpoint = serializers.CharField(source='get_api_endpoint', read_only=True)
    owner = UserSerializer(read_only=True)
    time = TimestampField()
    title = serializers.CharField(source='event', default=u'闹钟')

    class Meta:
        model = Remind
        fields = ('title', 'time', 'owner', 'id', 'defer', 'desc')
        read_only_fields = ('owner', 'id')

    def create(self, validated_data):
        raise PermissionDenied()
