# coding: utf-8
from __future__ import unicode_literals, absolute_import
from django.conf.urls import url, include
from django.views.generic import RedirectView
from rest_framework import routers
from remind.views import IndexView, RemindViewSet, media_proxy

router = routers.SimpleRouter()
router.register(r'', RemindViewSet, base_name='remind')

urlpatterns = [
    url(r'^$', IndexView.as_view(), name='remind_index'),
    url(r'^(?P<pk>\w{32})$', RedirectView.as_view(url='/reminds/#/%(pk)s', permanent=False)),
    url(r'^api/', include(router.urls)),
    url(r'^media/(?P<media_id>.+)$', media_proxy, name='media_downloader'),
]
