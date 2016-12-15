# coding: utf-8
from __future__ import unicode_literals, absolute_import

from datetime import timedelta
from django.test import TestCase
from django.utils import timezone
from remind.serializers import RemindSerializer, TimestampField
from remind.models import Remind


class RemindSerializerTestCase(TestCase):

    def setUp(self):
        self.r = Remind(time=timezone.now(), owner_id='miao', event='吃饭', desc='吃饭饭', done=True)
        self.r.save()

    def test_change_defer(self):
        update_data = {
            'title': self.r.event,
            'time': TimestampField().to_representation(self.r.time),
            'defer': -2*60
        }
        self.assertTrue(self.r.done)
        serializer = RemindSerializer(data=update_data, instance=self.r)
        self.assertTrue(serializer.is_valid())
        serializer.save()
        self.assertFalse(self.r.done)
        self.assertEqual(self.r.defer, -2*60)
        self.assertEqual(self.r.notify_time, self.r.time+timedelta(minutes=self.r.defer))

        update_data['defer'] = 2*24*60
        serializer = RemindSerializer(data=update_data, instance=self.r)
        self.assertTrue(serializer.is_valid())
        serializer.save()
        self.assertEqual(self.r.defer, 2*24*60)

    def test_uuid_format(self):
        serializer = RemindSerializer(instance=self.r)
        self.assertRegexpMatches(serializer.data['id'], r'\w{32}')

    def test_default_title(self):
        r = Remind(time=timezone.now(), owner_id='miao', desc='吃饭饭', done=True)
        r.save()
        serializer = RemindSerializer(instance=r)
        self.assertEqual(serializer.data['title'], Remind.default_title)

    def test_read_only_fields(self):
        update_data = {
            'id': '123',
            'owner': {
                'id': '123'
            },
            'title': self.r.event,
            'time': TimestampField().to_representation(self.r.time),
            'aaa': 1
        }
        serializer = RemindSerializer(data=update_data, initial=self.r)
        self.assertTrue(serializer.is_valid())
        self.assertNotIn('id', serializer.validated_data)
        self.assertNotIn('owner', serializer.validated_data)
        self.assertNotIn('aaa', serializer.validated_data)