from django.http import HttpRequest

from celery import task
from celery.task.schedules import crontab
from celery.decorators import periodic_task

__author__ = 'apredoi'

#from django_cron import cronScheduler, Job
from status_cron.views import *
from main.models import Module
#
#class CheckPassiveHosts(Job):
#    run_every = 60 #seconds
#
#    def job(self):
#        modules = Module.objects.filter(module_type='passive')
#        print "running check passive hosts cron"
#        for module in modules:
#            check_passive_hosts_task(HttpRequest(), module.id)

@periodic_task(run_every=crontab(hour="*", minute="*/1", day_of_week="*"))
def check_passive_monitors():
    modules = Module.objects.filter(module_type='passive')

    request = HttpRequest()
    request.META['HTTP_X_CELERY_CRON'] = 'true'

    for module in modules:
        check_passive_hosts_task.delay(request, module.id)


@periodic_task(run_every=crontab(hour="*", minute="*/5", day_of_week="*"))
def send_notifications():
    notifications = Notification.objects.filter(sent_at=None, send=True).order_by('-created_at')

    request = HttpRequest()
    request.META['HTTP_X_CELERY_CRON'] = 'true'

    for notification in notifications:
        send_notification_task.delay(request, notification.id)


#class CheckNotifications(Job):
#    run_every = 120 #seconds
#
#
#    def job(self):
#        check_notifications(HttpRequest())

#cronScheduler.register(CheckPassiveHosts)
#cronScheduler.register(CheckNotifications)