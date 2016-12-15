#coding: utf-8
from __future__ import unicode_literals, absolute_import
import logging
from datetime import timedelta
from django.views.generic import TemplateView
from rest_framework import viewsets, pagination
from rest_framework.generics import get_object_or_404
from rest_framework.exceptions import ValidationError
from django.utils import timezone
from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.urlresolvers import reverse
from django.conf import settings
from wechatpy import WeChatOAuth

from remind.models import Remind
from remind.serializers import RemindSerializer

logger = logging.getLogger(__name__)
oauth_client = WeChatOAuth(
    app_id=settings.WX_APPID,
    secret=settings.WX_APPSECRET,
    redirect_uri='abc',
    scope='snsapi_base',
    state='remind_list'
)


class WechatUserMixin(LoginRequiredMixin):

    def get_login_url(self):
        oauth_client.redirect_uri = self.request.build_absolute_uri(reverse('oauth_complete'))
        return oauth_client.authorize_url


class IndexView(WechatUserMixin, TemplateView):
    template_name = 'index.html'


class DefaultCursorPagination(pagination.CursorPagination):
    ordering = 'time'
    page_size = 10

    def decode_cursor(self, request):
        if self.cursor_query_param not in request.query_params:
            # Remove immutability
            request.query_params._mutable = True
            # Set default cursor to yesterday, copied from encode_cursor
            querystring = pagination.urlparse.urlencode({'p': timezone.now() - timedelta(days=1)}, doseq=True)
            encoded = pagination.b64encode(querystring.encode('ascii')).decode('ascii')
            request.query_params[self.cursor_query_param] = encoded
        return super(DefaultCursorPagination, self).decode_cursor(request)


class RemindViewSet(WechatUserMixin, viewsets.ModelViewSet):

    http_method_names = ['get', 'patch', 'delete']
    serializer_class = RemindSerializer
    pagination_class = DefaultCursorPagination

    def get_queryset(self):
        return self.request.user.get_time_reminds()

    def get_object(self):
        # Don't check ownership hear for sharing
        return get_object_or_404(Remind.objects, **self.kwargs)

    def perform_create(self, serializer):
        raise ValidationError('Not supported')

    def perform_update(self, serializer):
        if serializer.instance.owner_id == self.request.user.pk:
            return super(RemindViewSet, self).perform_update(serializer)
        self.permission_denied(self.request, message=u'Unauthorized!')

    def perform_destroy(self, instance):
        user = self.request.user
        if instance.owner_id == user.pk:
            instance.delete()
            logger.info('User(%s) deleted a remind(%s)', user.nickname, unicode(instance))
        elif user.pk in instance.participants:
            instance.participants.remove(self.request.user.pk)
            logger.info('User(%s) quited a remind(%s)', user.nickname, unicode(instance))
        else:
            self.permission_denied(self.request, message=u'Unauthorized!')
