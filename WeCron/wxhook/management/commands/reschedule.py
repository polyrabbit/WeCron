# coding: utf-8
from __future__ import unicode_literals, absolute_import

from django.core.management import BaseCommand
from django.utils import timezone
from remind.models import Remind


class Command(BaseCommand):

    def handle(self, *args, **options):
        yesterday = timezone.now() - timezone.timedelta(days=4)
        reminds = Remind.objects.filter(notify_time__date=yesterday).all()
        for rem in reminds:
            if rem.reschedule():
                rem.done = False
                print rem
                rem.save()