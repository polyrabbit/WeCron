# coding: utf-8
import logging

from django.contrib.auth import authenticate
from django.contrib.auth import login
from django.http import HttpResponseRedirect, HttpResponseForbidden
from django.utils.http import url_has_allowed_host_and_scheme
from django.contrib.auth.signals import user_logged_in
from django.dispatch import receiver
from rest_framework import viewsets, mixins, authentication
from remind.views import WWWAuthenticateHeaderMixIn
from wechat_user.serializers import UserSerializer
from wechat_user.backends import SubscribedTokenAuthentication, authorize_url

logger = logging.getLogger(__name__)


def OAuthComplete(request, *args, **kwargs):
    redirect_to = request.GET.get('state', '/')
    if not url_has_allowed_host_and_scheme(redirect_to, {request.get_host()}, request.is_secure()):
        redirect_to = '/'
    if request.user.is_authenticated:
        return HttpResponseRedirect(redirect_to)
    if 'code' in request.GET:
        user = authenticate(
                request,
                code=request.GET['code'],
                redirect_uri=request.build_absolute_uri(),
                state=None)
        if user:
            login(request, user)
            return HttpResponseRedirect(redirect_to)
        return HttpResponseForbidden("验证失败")
    # No code: the user declined to share the nickname and avatar, log in silently instead
    return HttpResponseRedirect(authorize_url(request, redirect_to, scope='snsapi_base'))


@receiver(user_logged_in)
def signals_receiver(sender, request, user, **kwargs):
    logger.info('User %s successfully logged into web page', user.get_full_name())


class ProfileViewSet(WWWAuthenticateHeaderMixIn, mixins.RetrieveModelMixin,
                   mixins.UpdateModelMixin, viewsets.GenericViewSet):
    http_method_names = ['patch', 'get']
    authentication_classes = (authentication.SessionAuthentication, SubscribedTokenAuthentication)
    serializer_class = UserSerializer

    def get_object(self):
        # Don't check ownership hear for sharing
        return self.request.user