#coding: utf-8
from __future__ import unicode_literals, absolute_import
import logging
from datetime import datetime

from django.utils.dateformat import format
from django.contrib.auth import get_user_model
from django.utils.timezone import utc
from rest_framework import serializers
from rest_framework.exceptions import ValidationError, PermissionDenied
from common import wechat_client
from remind.models import Remind

logger = logging.getLogger(__name__)
UserModel = get_user_model()


# class AuthorizationMixin(object):
#
#     def run_validation(self, *args, **kwargs):
#         ctx = self.context
#         if self.parent.instance.owner_id != ctx['request'].user.pk:
#             return ctx['view'].permission_denied(ctx['request'], message=u'Unauthorized!')
#         return super(AuthorizationMixin, self).run_validation(*args, **kwargs)


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


class TitleField(serializers.CharField):

    def to_representation(self, value):
        return super(TitleField, self).to_representation(value) or Remind.default_title


class UserSerializer(serializers.ModelSerializer):
    id = serializers.CharField(source='openid', read_only=True)

    class Meta:
        model = UserModel
        fields = ('nickname', 'headimgurl', 'id')


class ParticipantSerializer(serializers.Field):

    def to_internal_value(self, participants):
        logger.info('User(%s) subscribes a remind(%s)',
                    self.parent.context['request'].user.nickname, unicode(self.parent.instance))
        return list(set(p['id'] for p in participants if UserModel.objects.filter(pk=p['id'], subscribe=True).first()))

    def to_representation(self, participant_id_list):
        active_participants = []
        for uid in participant_id_list:
            user = UserModel.objects.filter(pk=uid, subscribe=True).first()
            if user:
                active_participants.append(user)
        serializer = UserSerializer(instance=active_participants, many=True)
        return serializer.data


class RemindSerializer(serializers.ModelSerializer):
    # apiEndpoint = serializers.CharField(source='get_api_endpoint', read_only=True)
    id = serializers.UUIDField(read_only=True, format='hex')
    owner = UserSerializer(read_only=True)
    time = TimestampField()
    title = TitleField(source='event')
    participants = ParticipantSerializer()
    participate_qrcode = serializers.SerializerMethodField()

    class Meta:
        model = Remind
        fields = ('title', 'time', 'owner', 'id', 'defer', 'desc', 'repeat', 'participants', 'participate_qrcode', 'media_id')
        read_only_fields = ('owner', 'id', 'media_id')

    def get_participate_qrcode(self, remind):
        user = self.context['request'].user
        if user.subscribe:
            return None
        logger.info('Creating QR code for %s', user.nickname)
        ticket = wechat_client.qrcode.create({
                'expire_seconds': 2592000,
                'action_name': 'QR_LIMIT_STR_SCENE',
                'action_info': {
                    'scene': {'scene_str': remind.id.hex},
                }
            })
        return wechat_client.qrcode.get_url(ticket)

    def create(self, validated_data):
        raise PermissionDenied()

    def save(self, **kwargs):
        self.instance.done = False
        return super(RemindSerializer, self).save(**kwargs)
