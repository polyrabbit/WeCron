from dateutil.relativedelta import relativedelta
from django.core.management import BaseCommand
from django.utils import timezone

from remind.models import Remind


class Command(BaseCommand):
    help = 'Delete reminds neither created nor due in the last 5 years'

    def handle(self, *args, **options):
        cutoff = timezone.now() - relativedelta(years=5)
        # Firing moves a repeating remind's time forward, so only dormant reminds have an old time.
        # time rather than notify_time, which is null on some reminds from 2016
        deleted, _ = Remind.objects.filter(time__lt=cutoff, create_time__lt=cutoff).delete()
        self.stdout.write('deleted %d reminds' % deleted)
