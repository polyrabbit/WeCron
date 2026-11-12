# coding: utf-8
from django.urls import include, re_path
from django.views.generic import RedirectView
from rest_framework import routers
from remind.views import IndexView, RemindViewSet, media_proxy, qr_code_view, share_post_view

router = routers.SimpleRouter()
router.register(r'', RemindViewSet, basename='remind')

urlpatterns = [
    re_path(r'^$', IndexView.as_view(), name='remind_index'),
    re_path(r'^(?P<pk>\w{32})$', RedirectView.as_view(url='/reminds/#/%(pk)s', permanent=False)),
    re_path(r'^api/', include(router.urls)),
    re_path(r'^api/(?P<remind_id>\w{32})/qrcode/', qr_code_view, name='qrcode_url'),
    re_path(r'^api/(?P<remind_id>\w{32})/share_post/', share_post_view, name='remind_share_post'),
    re_path(r'^media/(?P<media_id>.+)$', media_proxy, name='media_downloader'),
]
