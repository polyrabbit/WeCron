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
    # WeChat no longer tells nicknames, users set their own
    nickname = serializers.CharField(max_length=40, required=False)
    # Only IANA names, get_timezone() falls back to the default for anything else
    timezone = serializers.ChoiceField(sorted(ALL_TIMEZONES), required=False)

    class Meta:
        model = UserModel
        fields = meta_fields + ('morning_greeting', 'notify_subscription', 'timezone')
        read_only_fields = ('headimgurl', 'id')

    def validate_nickname(self, value):
        # Nicknames go into text messages that carry <a> links
        if '<' in value or '>' in value:
            raise serializers.ValidationError('昵称不能包含 < 或 >')
        return value
