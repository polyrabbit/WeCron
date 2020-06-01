# coding: utf-8
from __future__ import unicode_literals, absolute_import
from django.conf.urls import url
from rest_framework import routers
from eosram.views import IndexView, EosRamAlertView

router = routers.SimpleRouter()

urlpatterns = [
    url(r'^$', IndexView.as_view(), name='ram_index'),
    url(r'^api/$', EosRamAlertView.as_view(), name='ram_alert'),
]
