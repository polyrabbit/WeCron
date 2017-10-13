#coding: utf-8
from __future__ import unicode_literals, absolute_import
import logging
import time
from urllib import quote_plus

from rest_framework import viewsets, permissions, pagination, authentication
from rest_framework.generics import get_object_or_404
from django.views.generic import TemplateView
from django.http import Http404, StreamingHttpResponse
from django.utils import timezone
from django.core.urlresolvers import reverse
from django.conf import settings
from wechatpy import WeChatOAuth, WeChatClientException
from wechatpy.utils import random_string

from remind.models import Remind
from remind.serializers import RemindSerializer
from common import wechat_client

logger = logging.getLogger(__name__)


class IndexView(TemplateView):
    template_name = 'index.html'
    
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
        return ctx


class CursorPaginationStartsToday(pagination.CursorPagination):
    # Don't know why but it seems slicing in Django queryset will change
    # list order when their keys are all the same, so add "create_time" as a second key to sort.
    ordering = ('time', 'create_time')
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
        return super(CursorPaginationStartsToday, self).decode_cursor(request)


class WWWAuthenticateHeaderMixIn(object):
    permission_classes = (permissions.IsAuthenticated,)

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


class RemindViewSet(WWWAuthenticateHeaderMixIn, viewsets.ModelViewSet):
    http_method_names = ['post', 'get', 'patch', 'delete']
    authentication_classes = (authentication.SessionAuthentication, authentication.TokenAuthentication)
    serializer_class = RemindSerializer
    pagination_class = CursorPaginationStartsToday

    def get_queryset(self):
        return self.request.user.get_time_reminds()

    def get_object(self):
        # Don't check ownership hear for sharing
        return get_object_or_404(Remind.objects, **self.kwargs)

    def get_throttles(self):
        if self.action == 'create':
            self.throttle_scope = 'remind.' + self.action
        return super(RemindViewSet, self).get_throttles()

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


def media_proxy(request, media_id):
    try:
        resp = wechat_client.media.download(media_id)
        # import requests
        # resp = requests.get('http://b.hackernews.im/dl/song.mp3')
    except WeChatClientException as e:
        raise Http404(e)

    response = StreamingHttpResponse(
        (chunk for chunk in resp.iter_content(512 * 1024)),
        content_type=resp.headers.get('content-type'), status=resp.status_code)

    return response
