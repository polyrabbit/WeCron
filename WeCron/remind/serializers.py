#coding: utf-8
from __future__ import unicode_literals, absolute_import
import logging
from datetime import datetime

from django.utils.dateformat import format
from django.contrib.auth import get_user_model
from django.utils import timezone
from django.core.urlresolvers import reverse
from rest_framework import serializers
from rest_framework.exceptions import ValidationError, PermissionDenied
from remind.utils import get_qrcode_url
from remind.models import Remind
from remind.signals import participant_modified


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
            return datetime.fromtimestamp(int(value)/1000.0, timezone.utc)
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
                    self.parent.context['request'].user.get_full_name(), unicode(self.parent.instance))
        participant_modified.send(sender=self.parent.instance, participant=self.parent.context['request'].user, add=True)
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
    participants = ParticipantSerializer(default=list)
    participate_qrcode = serializers.SerializerMethodField()
    post_url = serializers.SerializerMethodField()

    class Meta:
        model = Remind
        fields = ('title', 'time', 'owner', 'id', 'defer', 'desc', 'repeat',
                  'participants', 'participate_qrcode', 'media_id', 'post_url', 'external_url')
        read_only_fields = ('owner', 'id', 'media_id')

    _created = False

    def get_participate_qrcode(self, remind):
        user = self.context['request'].user
        # If current user is subscribed and uses session authentication,
        # for token authentication is used for API, when doing an API request, the QR code should be returned.
        if user.subscribe and not self._created:
            return None
        logger.info('%s requests QR code for %s', user.get_full_name(), unicode(remind))
        return get_qrcode_url(remind.id.hex)

    def create(self, validated_data):
        self._created = True
        validated_data['owner'] = self.context['request'].user
        if 'time' in validated_data and validated_data['time'] <= timezone.now():
            raise ValidationError('不能设一个过去的提醒: %s' % validated_data['time'].strftime('%Y-%m-%d %H:%M'))
        return super(RemindSerializer, self).create(validated_data)

    def update(self, instance, validated_data):
        instance.done = False
        return super(RemindSerializer, self).update(instance, validated_data)

    def get_post_url(self, remind):
        return self.context['request'].build_absolute_uri(
            reverse('remind_share_post', kwargs={'remind_id': remind.pk.hex}))