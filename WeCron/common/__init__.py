from django.conf import settings

from wechat_sdk import WechatBasic

access_token_manager = WechatBasic(
    appid=settings.WX_APPID,
    appsecret=settings.WX_APPSECRET
)

def get_access_token():
    """There can only be one access token at the same time,
    and an access token expires in 2 hours.
    """
    return access_token_manager.access_token
