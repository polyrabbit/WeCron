# coding: utf-8
from httmock import urlmatch, response


@urlmatch(netloc=r'(.*\.)?api\.weixin\.qq\.com$', path='/cgi-bin/token')
def access_token_mock(url, request):
    content = {
        "access_token": "1234567890",
        "expires_in": 7200
    }
    headers = {
        'Content-Type': 'application/json'
    }
    return response(200, content, headers, request=request)
