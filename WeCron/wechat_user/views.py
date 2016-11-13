#coding: utf-8
from __future__ import unicode_literals, absolute_import
import logging

from django.contrib.auth import authenticate
from django.contrib.auth import login
from django.http import HttpResponseRedirect, HttpResponseForbidden
from django.core.urlresolvers import reverse, NoReverseMatch
from django.contrib.auth.signals import user_logged_in
from django.dispatch import receiver
from django.conf import settings

logger = logging.getLogger(__name__)


def OAuthComplete(request, *args, **kwargs):
    try:
        redirect_to = reverse(request.GET['state'])
    except (NoReverseMatch, KeyError):
        redirect_to = reverse('index')
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