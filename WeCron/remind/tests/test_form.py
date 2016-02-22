# coding: utf-8
from __future__ import unicode_literals, absolute_import

from datetime import timedelta
from django.test import TestCase
from django.utils import timezone
from remind.forms import RemindForm
from remind.models import Remind


class RemindFormTestCase(TestCase):

    def setUp(self):
        self.r = Remind(time=timezone.now(), owner_id='miao', event='吃饭', desc='吃饭饭', done=True)
        self.r.save()

    def test_change_defer(self):
        form_data = {
            'event': self.r.event,
            'time': self.r.time.strftime('%Y-%m-%dT%H:%M'),
            'defer': '提前 2 小时',
            'desc': self.r.desc
        }
        self.assertTrue(self.r.done)
        form = RemindForm(data=form_data, instance=self.r)
        form.save()
        self.assertTrue(form.is_valid())
        self.assertFalse(self.r.done)
        self.assertEqual(self.r.defer, -2*60)
        self.assertEqual(self.r.notify_time, self.r.time+timedelta(minutes=self.r.defer))

        form_data['defer'] = '延后 2 天'
        form = RemindForm(data=form_data, instance=self.r)
        form.save()
        self.assertEqual(self.r.defer, 2*24*60)
