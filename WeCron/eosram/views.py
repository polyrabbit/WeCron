# coding: utf-8
from __future__ import unicode_literals
import time
import logging

from django.views.generic import TemplateView
from django.conf import settings
from wechatpy.utils import random_string
from rest_framework import authentication
from rest_framework.generics import RetrieveUpdateAPIView
from django.http import JsonResponse

from common import wechat_client
from eosram.models import PriceThresholdChange, PricePercentageChange, Profile
from eosram.serializers import ThresholdSerializer, PercentageSerializer
from remind.views import WWWAuthenticateHeaderMixIn
from eosram.management.commands.checkPrice import EOS_ACCOUNT

logger = logging.getLogger(__name__)


class IndexView(TemplateView):
    template_name = 'eosram/index.html'

    def get_context_data(self, **kwargs):
        ctx = super(IndexView, self).get_context_data(**kwargs)
        timestamp = time.time()
        nonce_str = random_string(32)
        ticket = wechat_client.jsapi.get_jsapi_ticket()

        ctx['appId'] = settings.WX_APPID
        ctx['nonce_str'] = nonce_str
        ctx['timestamp'] = timestamp
        ctx['signature'] = wechat_client.jsapi.get_jsapi_signature(
            nonce_str, ticket, timestamp, self.request.build_absolute_uri())

        ctx['EOS_ACCOUNT'] = EOS_ACCOUNT
        ctx['eosram_profile'] = Profile.objects.filter(owner_id=self.request.user.pk).first()
        return ctx


class EosRamAlertView(WWWAuthenticateHeaderMixIn, RetrieveUpdateAPIView):
    http_method_names = ['post', 'get', 'patch', 'delete']
    authentication_classes = (authentication.SessionAuthentication, authentication.TokenAuthentication)

    def get_alerts(self):
        resp = {}

        alert_qs = PriceThresholdChange.objects.filter(owner=self.request.user)
        resp['threshold'] = ThresholdSerializer(alert_qs, many=True).data

        alert_qs = PricePercentageChange.objects.filter(owner=self.request.user)
        resp['percent'] = PercentageSerializer(alert_qs, many=True).data
        return resp

    def get(self, request, *args, **kwargs):

        return JsonResponse(self.get_alerts())

    def patch(self, request, *args, **kwargs):

        queryset = PriceThresholdChange.objects.filter(owner=self.request.user)
        for alert_json in request.data.get('threshold', []):
            if alert_json.get('id'):
                alert = queryset.filter(id=alert_json['id']).first()
                if not alert:
                    logger.warning('Cannot find id(%s) from database', alert_json['id'])
                    continue
                if alert_json.get('threshold'):
                    # Have id and threshold -> update
                    serializer = ThresholdSerializer(alert, data=dict(alert_json, owner=self.request.user.pk))
                    if serializer.is_valid():
                        logger.info('User(%s) updates a %s threshold remind(from %s to %s)',
                                    self.request.user.nickname, 'increasing' if alert_json['increase'] else 'decreasing',
                                    alert.threshold, alert_json['threshold'])
                        serializer.save()
                else:
                    # Have id and no threshold -> delete
                    logger.info('User(%s) deletes a %s threshold remind(%s)',
                                self.request.user.nickname, 'increasing' if alert_json['increase'] else 'decreasing',
                                alert.threshold)
                    alert.delete()
                    del alert_json['id']
            else:
                if alert_json.get('threshold'):
                    if queryset.count() > 100:
                        return JsonResponse({'errMsg': '保存失败，你的提醒数超过100啦~'})
                    # Have no id and threshold -> insert
                    serializer = ThresholdSerializer(data=dict(alert_json, owner=self.request.user.pk))
                    if serializer.is_valid():
                        logger.info('User(%s) adds a %s threshold remind(%s)',
                                    self.request.user.nickname, 'increasing' if alert_json['increase'] else 'decreasing',
                                    alert_json['threshold'])
                        serializer.save()
                        alert_json['id'] = serializer.instance.id
                # Have no id and no threshold -> noop

        queryset = PricePercentageChange.objects.filter(owner=self.request.user)
        for alert_json in request.data.get('percent', []):
            if alert_json.get('id'):
                alert = queryset.filter(id=alert_json['id']).first()
                if not alert:
                    logger.warning('Cannot find id(%s) from database', alert_json['id'])
                    continue
                if alert_json.get('threshold'):
                    # Have id and threshold -> update
                    serializer = PercentageSerializer(alert, data=dict(alert_json, owner=self.request.user.pk))
                    if serializer.is_valid():
                        logger.info('User(%s) updates a %s percent remind(from %s to %s)',
                                    self.request.user.nickname, 'increasing' if alert_json['increase'] else 'decreasing',
                                    alert.threshold, alert_json['threshold'])
                        serializer.save()
                else:
                    # Have id and no threshold -> delete
                    logger.info('User(%s) deletes a %s percent remind(%s)',
                                self.request.user.nickname, 'increasing' if alert_json['increase'] else 'decreasing',
                                alert.threshold)
                    alert.delete()
                    del alert_json['id']
            else:
                if alert_json.get('threshold'):
                    if queryset.count() > 100:
                        return JsonResponse({'errMsg': '保存失败，你的提醒数超过100啦~'})
                    # Have no id and threshold -> insert
                    serializer = PercentageSerializer(data=dict(alert_json, owner=self.request.user.pk))
                    if serializer.is_valid():
                        logger.info('User(%s) adds a %s percent remind(%s)',
                                    self.request.user.nickname, 'increasing' if alert_json['increase'] else 'decreasing',
                                    alert_json['threshold'])
                        serializer.save()
                        alert_json['id'] = serializer.instance.id
                # Have no id and no threshold -> noop

        try:
            user_profile = Profile.objects.filter(owner_id=request.user.pk).first()
            if not user_profile:
                ref = request.GET.get('ref')
                user_profile = Profile.objects.create(owner_id=request.user.pk, ref=ref)
                if ref:
                    invitor = Profile.objects.filter(memo=ref).first()
                    if invitor:
                        invitor.add_reward(user_profile)
        except:
            logger.exception('Failed to set user reference')

        return JsonResponse(request.data)
