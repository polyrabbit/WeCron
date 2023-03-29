# coding: utf-8
from __future__ import unicode_literals, absolute_import
import logging

from django.contrib.auth import authenticate
from django.contrib.auth import login
from django.http import HttpResponseRedirect, HttpResponseForbidden
from django.contrib.auth.signals import user_logged_in
from django.dispatch import receiver
from rest_framework import viewsets, mixins, authentication
from remind.views import WWWAuthenticateHeaderMixIn
from wechat_user.serializers import UserSerializer

logger = logging.getLogger(__name__)


def OAuthComplete(request, *args, **kwargs):
    redirect_to = request.GET.get('state', '/')
    if request.user.is_authenticated():
        return HttpResponseRedirect(redirect_to)
    if 'code' in request.GET:
        user = authenticate(
                code=request.GET['code'],
                redirect_uri=request.build_absolute_uri(),
                state=None)
        if user:
            login(request, user)
            return HttpResponseRedirect(redirect_to)
    return HttpResponseForbidden("验证失败")


@receiver(user_logged_in)
def signals_receiver(sender, request, user, **kwargs):
    logger.info('User %s successfully logged into web page', user.get_full_name())


class ProfileViewSet(WWWAuthenticateHeaderMixIn, mixins.RetrieveModelMixin,
                   mixins.UpdateModelMixin, viewsets.GenericViewSet):
    http_method_names = ['patch', 'get']
    authentication_classes = (authentication.SessionAuthentication, authentication.TokenAuthentication)
    serializer_class = UserSerializer

    def get_object(self):
        # Don't check ownership hear for sharing
        return self.request.user