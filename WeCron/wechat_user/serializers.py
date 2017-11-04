#coding: utf-8
from __future__ import unicode_literals, absolute_import
import logging

from django.contrib.auth import get_user_model
from rest_framework import serializers

logger = logging.getLogger(__name__)
UserModel = get_user_model()

meta_fields = ('nickname', 'headimgurl', 'id')


class UserSerializer(serializers.ModelSerializer):
    id = serializers.CharField(source='openid', read_only=True)

    class Meta:
        model = UserModel
        fields = meta_fields + ('morning_greeting', 'notify_subscription', 'timezone')
        read_only_fields = meta_fields
