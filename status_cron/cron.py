from django.http import HttpRequest

__author__ = 'apredoi'

from django_cron import cronScheduler, Job
from status_cron.views import *
from main.models import Module

class CheckPassiveHosts(Job):
    run_every = 60 #seconds

    def job(self):
        modules = Module.objects.filter(module_type='passive')
        print "running check passive hosts cron"
        for module in modules:
            check_passive_hosts_task(HttpRequest(), module.id)


class CheckNotifications(Job):
    run_every = 120 #seconds

    def job(self):
        check_notifications(HttpRequest())

cronScheduler.register(CheckPassiveHosts)
cronScheduler.register(CheckNotifications)