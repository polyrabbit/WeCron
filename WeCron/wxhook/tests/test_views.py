# coding: utf-8
from __future__ import unicode_literals, absolute_import
from django.test import TestCase
from django.core.urlresolvers import reverse


class ViewsTestCase(TestCase):

    def test_validating_signature(self):
        echostr = 'GOOD'
        timestamp = '1500000000'
        nonce = 'nonce123'

        with self.settings(WX_SIGN_TOKEN='123'):
            sig_for_tocken_123 = '4e0d68d587d1433257aa2d409f1e4d3a431c0a89'
            resp = self.client.get(reverse('weixin_callback'),
                                   data={'echostr': echostr,
                                         'signature': sig_for_tocken_123,
                                         'timestamp': timestamp,
                                         'nonce': nonce})
            self.assertEqual(resp.status_code, 200)
            self.assertEqual(resp.content, echostr)

            resp = self.client.get(reverse('weixin_callback'),
                                   data={'echostr': echostr,
                                         'signature': 'xxx',
                                         'timestamp': timestamp,
                                         'nonce': nonce})
            self.assertEqual(resp.status_code, 200)
            self.assertNotEqual(resp.content, echostr)
