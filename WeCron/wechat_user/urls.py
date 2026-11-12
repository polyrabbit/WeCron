# coding: utf-8
from django.urls import re_path
from wechat_user.views import ProfileViewSet

profile_detail = ProfileViewSet.as_view({
    'get': 'retrieve',
    'patch': 'partial_update'
})

urlpatterns = [
    re_path(r'^api/$', profile_detail, name='profile-detail'),
]
