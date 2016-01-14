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
from django.conf.urls import include, url
from django.views.generic import TemplateView, RedirectView
from django.contrib import admin

from wxhook.views import WeiXinHook
from wechat_user.views import OAuthComplete

urlpatterns = [
     url(r'^$',
        RedirectView.as_view(url='https://github.com/polyrabbit/WeCron'), name='index'),
    url(r'^wxhook$', WeiXinHook.as_view(), name='weixin_callback'),
    url(r'^reminds/', include('remind.urls')),
    url(r'^login/weixin/', OAuthComplete, name='oauth_complete'),
    url(r'^under_construction$',
        TemplateView.as_view(template_name='under_construction.html'), name='under_construction'),

    # url(r'^admin/', include(admin.site.urls)),  # Tuning django's user model is a disaster
]
