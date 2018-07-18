import time
import logging

from django.views.generic import TemplateView
from django.conf import settings
from wechatpy.utils import random_string
from rest_framework import authentication
from rest_framework.generics import RetrieveUpdateAPIView
from django.http import JsonResponse

from common import wechat_client
from eosram.models import PriceThresholdChange, PricePercentageChange
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
        return ctx


class EosRamAlertView(WWWAuthenticateHeaderMixIn, RetrieveUpdateAPIView):
    http_method_names = ['post', 'get', 'patch', 'delete']
    authentication_classes = (authentication.SessionAuthentication, authentication.TokenAuthentication)

    def get(self, request, *args, **kwargs):
        resp = {'threshold': {'increase': {'increase': True}, 'decrease': {'increase': False}},
                'percent': {'increase': {'increase': True}, 'decrease': {'increase': False}}}

        inc_alert = PriceThresholdChange.objects.filter(owner=self.request.user, increase=True).first()
        if inc_alert is not None:
            resp['threshold']['increase'] = ThresholdSerializer(inc_alert).data
        dec_alert = PriceThresholdChange.objects.filter(owner=self.request.user, increase=False).first()
        if dec_alert is not None:
            resp['threshold']['decrease'] = ThresholdSerializer(dec_alert).data

        inc_alert = PricePercentageChange.objects.filter(owner=self.request.user, increase=True).first()
        if inc_alert is not None:
            resp['percent']['increase'] = PercentageSerializer(inc_alert).data
        dec_alert = PricePercentageChange.objects.filter(owner=self.request.user, increase=False).first()
        if dec_alert is not None:
            resp['percent']['decrease'] = PercentageSerializer(dec_alert).data

        return JsonResponse(resp)

    def patch(self, request, *args, **kwargs):
        alert = PriceThresholdChange.objects.filter(owner=self.request.user, increase=True).first()
        serializer = ThresholdSerializer(alert,
                                         data=dict(request.data['threshold']['increase'], owner=self.request.user.pk))
        if serializer.is_valid():
            serializer.save()
            logger.info('User(%s) adds a increasing threshold remind(%s)', self.request.user.nickname, serializer.data['threshold'])

        alert = PriceThresholdChange.objects.filter(owner=self.request.user, increase=False).first()
        serializer = ThresholdSerializer(alert,
                                         data=dict(request.data['threshold']['decrease'], owner=self.request.user.pk))
        if serializer.is_valid():
            serializer.save()
            logger.info('User(%s) adds a decreasing threshold remind(%s)', self.request.user.nickname, serializer.data['threshold'])

        alert = PricePercentageChange.objects.filter(owner=self.request.user, increase=True).first()
        serializer = PercentageSerializer(alert,
                                         data=dict(request.data['percent']['increase'], owner=self.request.user.pk))
        if serializer.is_valid():
            serializer.save()
            logger.info('User(%s) adds a increasing percent remind(%s)', self.request.user.nickname, serializer.data['threshold'])

        alert = PricePercentageChange.objects.filter(owner=self.request.user, increase=False).first()
        serializer = PercentageSerializer(alert,
                                         data=dict(request.data['percent']['decrease'], owner=self.request.user.pk))
        if serializer.is_valid():
            serializer.save()
            logger.info('User(%s) adds a decreasing percent remind(%s)', self.request.user.nickname, serializer.data['threshold'])

        return JsonResponse(request.data)
