# coding: utf-8
from __future__ import unicode_literals, absolute_import

from django.test import TestCase
from django.utils import timezone
from remind.models import Remind


class RemindModelTestCase(TestCase):
    def test_add_add_participant(self):
        r = Remind(time=timezone.now(), owner_id='miao', event='吃饭', desc='吃饭饭')
        r.save()
        r.add_participant('abc')
        r.add_participant('abc')

        self.assertEqual(r.participants, ['abc'])