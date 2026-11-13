#coding: utf-8
import logging
import time
from urllib.parse import quote_plus

from rest_framework import viewsets, permissions, pagination, authentication
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.generics import get_object_or_404
from django.views.generic import TemplateView
from django.http import Http404, StreamingHttpResponse, JsonResponse, HttpResponse
from django.utils import timezone
from django.urls import reverse
from django.conf import settings
from wechatpy import WeChatOAuth, WeChatClientException
from wechatpy.utils import random_string

from common import wechat_client
from remind.models import Remind
from wechat_user.backends import SubscribedTokenAuthentication
from remind.serializers import RemindSerializer
from remind.signals import participant_modified
from remind.utils import get_qrcode_url
from remind.share_post import draw_post

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
            # Default cursor starts from today
            today = timezone.localtime(timezone.now()).replace(hour=0, minute=0, second=0, microsecond=0)
            return pagination.Cursor(offset=0, reverse=False, position=str(today))
        return super(CursorPaginationStartsToday, self).decode_cursor(request)


class WWWAuthenticateHeaderMixIn(object):
    permission_classes = (permissions.IsAuthenticated,)

    def initial(self, request, *args, **kwargs):
        super(WWWAuthenticateHeaderMixIn, self).initial(request, *args, **kwargs)
        # Token authenticated users are not visible to TimezoneMiddleware
        if hasattr(request.user, 'activate_timezone'):
            request.user.activate_timezone()

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
    authentication_classes = (authentication.SessionAuthentication, SubscribedTokenAuthentication)
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

    @action(detail=True, methods=['post'])
    def subscribe(self, request, pk=None):
        # Guests and unsubscribed users can't receive the notifications
        if not request.user.subscribe:
            self.permission_denied(request, message='请先关注公众号')
        remind = self.get_object()
        if remind.add_participant(request.user.pk):
            logger.info('User(%s) subscribes a remind(%s)', request.user.get_full_name(), remind)
        return Response(self.get_serializer(remind).data)

    def perform_update(self, serializer):
        if serializer.instance.owner_id != self.request.user.pk:
            self.permission_denied(self.request, message=u'Unauthorized!')
        super(RemindViewSet, self).perform_update(serializer)

    def perform_destroy(self, instance):
        user = self.request.user
        if instance.owner_id == user.pk:
            instance.delete()
            logger.info('User(%s) deletes a remind(%s)', user.get_full_name(), instance)
        elif instance.remove_participant(user.pk):
            logger.info('User(%s) quites a remind(%s)', user.get_full_name(), instance)
            participant_modified.send(sender=instance, participant=user, add=False)
        else:
            self.permission_denied(self.request, message=u'Unauthorized!')


def media_proxy(request, media_id):
    try:
        resp = wechat_client.media.download(media_id)
    except WeChatClientException as e:
        raise Http404(e)

    response = StreamingHttpResponse(
        (chunk for chunk in resp.iter_content(512 * 1024)),
        content_type=resp.headers.get('content-type'), status=resp.status_code)

    return response


def qr_code_view(request, remind_id):
    return JsonResponse({'qrcodeUrl': get_qrcode_url(remind_id)})


def share_post_view(request, remind_id):
    user = None
    if request.user.is_authenticated:
        user = request.user
    remind = get_object_or_404(Remind.objects, pk=remind_id)
    post_image = draw_post(remind, user)

    # Saving the image to the Django response object:
    response = HttpResponse(content_type='image/png')
    post_image.save(response, 'PNG')

    return response
