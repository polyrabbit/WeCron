#coding: utf-8
from __future__ import unicode_literals, absolute_import
import atexit
import logging

from apscheduler.schedulers.background import BackgroundScheduler
from django.conf import settings

logger = logging.getLogger(__name__)
scheduler = BackgroundScheduler()

# import sys, socket
#
# try:
#     sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
#     sock.bind(("127.0.0.1", 47200))
# except socket.error:
#     print "!!!scheduler already started, DO NOTHING"
# else:
#     from apscheduler.schedulers.background import BackgroundScheduler
#     scheduler = BackgroundScheduler()
#     scheduler.start()
#     print "scheduler started"
# http://stackoverflow.com/questions/16053364


@atexit.register
def shutdown_scheduler():
    logger.info('Shutting down scheduler')
    scheduler.shutdown()


@scheduler.scheduled_job('cron', hour=3, jobstore='default', timezone=settings.TIME_ZONE)
def update_user_info():
    print "+"*10, 'updating user info'

scheduler.start()