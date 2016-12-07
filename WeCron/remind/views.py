#coding: utf-8
from __future__ import unicode_literals, absolute_import
import logging
from datetime import timedelta
from django.views.generic.edit import UpdateView
from django.views.generic import TemplateView
from rest_framework import viewsets, pagination
from rest_framework.generics import get_object_or_404
from rest_framework.exceptions import ValidationError
from django.utils import timezone
from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.urlresolvers import reverse
from django.conf import settings
from django.http import HttpResponseForbidden
from django.forms import DateTimeField
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


class RemindViewSet(WechatUserMixin, viewsets.ModelViewSet):

    http_method_names = ['get', 'post', 'delete']
    serializer_class = RemindSerializer
    pagination_class = pagination.PageNumberPagination
    page_size = 10
    # page_size_query_param = 'page_size'
    dtparser = DateTimeField()

    def get_queryset(self):
        if self.before:
            query = self.request.user.get_time_reminds().filter(
                        time__date__lt=self.start_date()
                    ).reverse()
        else:
            query = self.request.user.get_time_reminds().filter(
                        time__date__gt=self.start_date()
                    )
        return query.order_by(self.get_ordering())

    @property
    def before(self):
        return 'before' in self.request.GET

    def get_ordering(self):
        if self.before:
            return '-time'
        return 'time'

    def start_date(self):
        try:
            dtstr = self.request.GET['date']
            return self.dtparser.to_python(dtstr)
        except:
            return timezone.now() - timedelta(days=1)

    def get_object(self):
        remind = get_object_or_404(self.request.user.get_time_reminds(), **self.kwargs)
        if self.request.method == 'DELETE':
            if remind.owner_id != self.request.user.pk:
                self.permission_denied(self.request, message=u'Unauthorized!')
        return remind

    def perform_create(self, serializer):
        raise ValidationError('Not supported')

    def perform_update(self, serializer):
        return super(RemindViewSet, self).perform_update(serializer)

    def perform_destroy(self, instance):
        super(RemindViewSet, self).perform_destroy(instance)
        logger.info('User(%s) deleted a remind(%s)', self.request.user.nickname, unicode(instance))


class RemindUpdateView(WechatUserMixin, UpdateView):
    model = Remind
    template_name = 'remind/remind_update.html'
    context_object_name = 'remind'

    def get_success_url(self):
        return reverse('remind_update', kwargs={'pk': self.kwargs['pk']})

    def post(self, request, *args, **kwargs):
        rem = self.get_object()
        if rem.owner_id != request.user.pk:
            return HttpResponseForbidden()
        return super(RemindUpdateView, self).post(request, *args, **kwargs)
#
#
# class RemindDeleteView(WechatUserMixin, DeleteView):
#     success_url = reverse_lazy('remind_list')
#     model = Remind
#
#     def delete(self, request, *args, **kwargs):
#         try:
#             self.object = self.get_object()
#         except Http404:
#             return HttpResponseRedirect(self.success_url)
#         if self.object.owner_id == request.user.pk:
#             logger.info('User %s removed remind: %s', request.user.nickname, self.object.event)
#             self.object.delete()
#         elif request.user.pk in self.object.participants:
#             logger.info('User %s quited remind: %s', request.user.nickname, self.object.event)
#             self.object.remove_participant(request.user.pk)
#         else:
#             return HttpResponseForbidden()
#         return HttpResponseRedirect(self.get_success_url())
#
#     get = delete
