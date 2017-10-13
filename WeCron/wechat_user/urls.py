# coding: utf-8
from __future__ import unicode_literals, absolute_import
from django.conf.urls import url
from wechat_user.views import ProfileViewSet

profile_detail = ProfileViewSet.as_view({
    'get': 'retrieve',
    'patch': 'partial_update'
})

urlpatterns = [
    url(r'^api/$', profile_detail, name='profile-detail'),
]
