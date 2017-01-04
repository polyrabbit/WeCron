#coding: utf-8
from __future__ import unicode_literals, absolute_import
import logging
from urllib import quote_plus
from rest_framework import viewsets, permissions, pagination
from rest_framework.generics import get_object_or_404
from rest_framework.exceptions import ValidationError
from django.views.generic import TemplateView
from django.utils import timezone
from django.core.urlresolvers import reverse
from django.conf import settings
from wechatpy import WeChatOAuth

from remind.models import Remind
from remind.serializers import RemindSerializer

logger = logging.getLogger(__name__)


class IndexView(TemplateView):
    template_name = 'index.html'


class DefaultCursorPagination(pagination.CursorPagination):
    ordering = 'time'
    page_size = 10

    def decode_cursor(self, request):
        if self.cursor_query_param not in request.query_params:
            # Remove immutability
            request.query_params._mutable = True
            # Set default cursor to yesterday, copied from encode_cursor
            querystring = pagination.urlparse.urlencode(
                {'p': timezone.localtime(timezone.now()).replace(hour=0, minute=0, second=0, microsecond=0)},
                                                        doseq=True)
            encoded = pagination.b64encode(querystring.encode('ascii')).decode('ascii')
            request.query_params[self.cursor_query_param] = encoded
        return super(DefaultCursorPagination, self).decode_cursor(request)


class RemindViewSet(viewsets.ModelViewSet):

    http_method_names = ['get', 'patch', 'delete']
    permission_classes = (permissions.IsAuthenticated,)
    serializer_class = RemindSerializer
    pagination_class = DefaultCursorPagination

    def get_queryset(self):
        return self.request.user.get_time_reminds()

    def get_object(self):
        # Don't check ownership hear for sharing
        return get_object_or_404(Remind.objects, **self.kwargs)

    def get_authenticate_header(self, request):
        """
        If a request is unauthenticated, set wechat login url in the WWW-Authenticate header.
        """
        current_state = request.META.get('HTTP_X_REFERER') or request.META.get('HTTP_REFERER', '/')
        oauth_client = WeChatOAuth(
            app_id=settings.WX_APPID,
            secret=settings.WX_APPSECRET,
            redirect_uri=self.request.build_absolute_uri(reverse('oauth_complete')),
            scope='snsapi_base',
            state=quote_plus(current_state)
        )
        return oauth_client.authorize_url

    def perform_create(self, serializer):
        raise ValidationError('Not supported')

    def perform_update(self, serializer):
        # TODO: refine me
        # Check permission in serializer, for 'participants' needs no authorization
        if serializer.instance.owner_id == self.request.user.pk or serializer.initial_data.keys() == ['participants']:
            return super(RemindViewSet, self).perform_update(serializer)
        self.permission_denied(self.request, message=u'Unauthorized!')

    def perform_destroy(self, instance):
        user = self.request.user
        if instance.owner_id == user.pk:
            instance.delete()
            logger.info('User(%s) deletes a remind(%s)', user.nickname, unicode(instance))
        elif user.pk in instance.participants:
            instance.participants.remove(self.request.user.pk)
            instance.save(update_fields=['participants'])
            logger.info('User(%s) quites a remind(%s)', user.nickname, unicode(instance))
        else:
            self.permission_denied(self.request, message=u'Unauthorized!')
