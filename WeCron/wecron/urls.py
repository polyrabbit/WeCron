"""wecron URL Configuration

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/1.8/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  url(r'^$', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  url(r'^$', Home.as_view(), name='home')
Including another URLconf
    1. Add an import:  from blog import urls as blog_urls
    2. Add a URL to urlpatterns:  url(r'^blog/', include(blog_urls))
"""
from django.urls import include, re_path
from django.views.generic import TemplateView, RedirectView

from wxhook.views import WeiXinHook
from wechat_user.views import OAuthComplete
from wechat_user.miniapp import MiniAppLoginView

urlpatterns = [
    re_path(r'^$',
        TemplateView.as_view(template_name='common_index.html'), name='index'),
    re_path(r'^wxhook$', WeiXinHook.as_view(), name='weixin_callback'),
    re_path(r'^reminds/', include('remind.urls')),
    re_path(r'^profile/', include('wechat_user.urls')),
    re_path(r'^login/weixin/', OAuthComplete, name='oauth_complete'),
    re_path(r'^miniprogram/login$', MiniAppLoginView.as_view(), name='miniapp_login'),
    re_path(r'^under_construction$',
        TemplateView.as_view(template_name='under_construction.html'), name='under_construction'),

    re_path(r'^eosram/', include('eosram.urls')),
    # url(r'^admin/', include(admin.site.urls)),  # Tuning django's user model is a disaster
]
