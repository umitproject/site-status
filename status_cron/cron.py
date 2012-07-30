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
def celery_task():
    modules = Module.objects.filter(module_type='passive')
    print "running check passive hosts cron"
    for module in modules:
        check_passive_hosts_task.delay(HttpRequest(), module.id)


#class CheckNotifications(Job):
#    run_every = 120 #seconds
#
#
#    def job(self):
#        check_notifications(HttpRequest())

#cronScheduler.register(CheckPassiveHosts)
#cronScheduler.register(CheckNotifications)