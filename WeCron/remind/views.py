#coding: utf-8
from __future__ import unicode_literals, absolute_import
import logging
from datetime import timedelta
from django.views.generic.edit import UpdateView, DeleteView
from django.views.generic import ListView
from django.utils import timezone
from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.urlresolvers import reverse, reverse_lazy
from django.conf import settings
from django.http import HttpResponseForbidden, Http404, HttpResponseRedirect
from django.forms import DateTimeField
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

    dtparser = DateTimeField()

    def get_login_url(self):
        oauth_client.redirect_uri = self.request.build_absolute_uri(reverse('oauth_complete'))
        return oauth_client.authorize_url

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


class RemindUpdateView(LoginRequiredMixin, UpdateView):
    model = Remind
    fields = ['time', 'desc', 'event']
    template_name = 'remind/remind_update.html'
    context_object_name = 'remind'

    def get_success_url(self):
        return reverse('remind_update', kwargs={'pk': self.kwargs['pk']})

    def get_login_url(self):
        oauth_client.redirect_uri = self.request.build_absolute_uri(reverse('oauth_complete'))
        return oauth_client.authorize_url

    def post(self, request, *args, **kwargs):
        rem = self.get_object()
        if rem.owner != request.user:
            return HttpResponseForbidden()
        return super(RemindUpdateView, self).post(request, *args, **kwargs)

    def form_valid(self, form):
        self.object.done = False
        self.object.save()
        return super(RemindUpdateView, self).form_valid(form)


class RemindDeleteView(LoginRequiredMixin, DeleteView):
    success_url = reverse_lazy('remind_list')
    model = Remind

    def delete(self, request, *args, **kwargs):
        rem = self.get_object()
        if rem.owner != request.user:
            return HttpResponseForbidden()
        try:
            super(RemindDeleteView, self).delete(request, *args, **kwargs)
        except Http404:
            return HttpResponseRedirect(self.success_url)

    get = delete