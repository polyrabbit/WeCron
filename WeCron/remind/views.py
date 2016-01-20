#coding: utf-8
from __future__ import unicode_literals, absolute_import
import logging
from django.views.generic.edit import UpdateView
from django.views.generic import ListView, DetailView
from django.utils import timezone
from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.urlresolvers import reverse
from django.conf import settings
from wechatpy import WeChatOAuth

from remind.models import Remind

logger = logging.getLogger(__name__)
oauth_client = WeChatOAuth(
    app_id=settings.WX_APPID,
    secret=settings.WX_APPSECRET,
    redirect_uri='abc',
    scope='snsapi_base',
    state='remind_list'
)


class RemindListView(LoginRequiredMixin, ListView):
    context_object_name = 'reminds'
    redirect_field_name = None

    def get_login_url(self):
        oauth_client.redirect_uri = self.request.build_absolute_uri(reverse('oauth_complete'))
        return oauth_client.authorize_url

    def get_queryset(self):
        # return Remind.objects.order_by('time')
        return self.request.user.get_time_reminds().filter(
            time__date__gte=timezone.now()
        ).order_by('time')


class RemindDetailView(DetailView):
    model = Remind
    context_object_name = 'remind'


class RemindUpdateView(UpdateView):
    model = Remind
    fields = ['time', 'desc', 'event']
    template_name = 'remind/remind_update.html'
    context_object_name = 'remind'

    def get_success_url(self):
        return reverse('remind_update', kwargs={'pk': self.kwargs['pk']})
