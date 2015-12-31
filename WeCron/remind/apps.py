from django.apps import AppConfig
from django.db.models.signals import post_save


class RemindConfig(AppConfig):

    name = 'remind'

    def ready(self):
        from models.scheduler import RemindScheduler
        # Remind = self.get_model('Remind')
        scheduler = RemindScheduler()
        post_save.connect(lambda *a, **k: scheduler.wakeup(),
                          sender='remind.Remind',
                          weak=False,
                          dispatch_uid='update-scheduler')
        scheduler.start()

