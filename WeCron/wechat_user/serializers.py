#coding: utf-8
import logging

from django.contrib.auth import get_user_model
from rest_framework import serializers

from wechat_user.models import ALL_TIMEZONES

logger = logging.getLogger(__name__)
UserModel = get_user_model()

meta_fields = ('nickname', 'headimgurl', 'id')


class UserSerializer(serializers.ModelSerializer):
    id = serializers.CharField(source='openid', read_only=True)
    # Only IANA names, get_timezone() falls back to the default for anything else
    timezone = serializers.ChoiceField(sorted(ALL_TIMEZONES), required=False)

    class Meta:
        model = UserModel
        fields = meta_fields + ('morning_greeting', 'notify_subscription', 'timezone')
        read_only_fields = meta_fields
