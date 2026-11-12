# coding: utf-8
from django.urls import re_path
from rest_framework import routers
from eosram.views import IndexView, EosRamAlertView

router = routers.SimpleRouter()

urlpatterns = [
    re_path(r'^$', IndexView.as_view(), name='ram_index'),
    re_path(r'^api/$', EosRamAlertView.as_view(), name='ram_alert'),
]
