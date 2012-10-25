from django.http import HttpRequest

from celery import task
from celery.task.schedules import crontab
from celery.decorators import periodic_task
from main.memcache import memcache
from settings import CELERY_CACHE_TIMEOUT


CHECK_HOST_KEY = 'check_passive_host_%s'
CHECK_NOTIFICATION_KEY = 'check_notification_%s'

__author__ = 'apredoi'

from status_cron.views import check_passive_url_task,check_passive_port_task,send_notification_task
from main.models import Module, Notification
import logging


@periodic_task(run_every=crontab(hour="*", minute="*/1", day_of_week="*"))
def check_passive_url_monitors():
    modules = Module.objects.filter(module_type='url_check')

    request = HttpRequest()
    request.META['HTTP_X_CELERY_CRON'] = 'true'

    for module in modules:
        passive_key = CHECK_HOST_KEY % module.id
        if memcache.get(passive_key,False):
            #this means that the check is already running
            logging.critical("Module id %s is already running"%module.id)
            continue
        memcache.set(passive_key,module,CELERY_CACHE_TIMEOUT)
        check_passive_url_task.apply_async((request, module.id))


@periodic_task(run_every=crontab(hour="*", minute="*/1", day_of_week="*"))
def check_passive_port_monitors():
    modules = Module.objects.filter(module_type='port_check')

    for module in modules:
        passive_key = CHECK_HOST_KEY % module.id
        if memcache.get(passive_key,False):
            #this means that the check is already running
            logging.critical("Module id %s is already running"%module.id)
            continue

        request = HttpRequest()
        request.META['HTTP_X_CELERY_CRON'] = 'true'

        memcache.set(passive_key,module, CELERY_CACHE_TIMEOUT)
        check_passive_port_task.apply_async((request, module.id))
    return True


@periodic_task(run_every=crontab(hour="*", minute="*/1", day_of_week="*"))
def send_notifications():
    notifications = Notification.objects.filter(sent_at=None, send=True).order_by('-created_at')

    for notification in notifications:
        if not notification.send:
            logging.info("Auto-send is disabled for notification %s." % notification.id)
            continue
        
        not_key = CHECK_NOTIFICATION_KEY % notification.id
        if memcache.get(not_key,False):
            #this means that the check is already running
            logging.critical("Module id %s is already running"%notification.id)
            continue

        request = HttpRequest()
        request.META['HTTP_X_CELERY_CRON'] = 'true'
        memcache.set(not_key,notification, CELERY_CACHE_TIMEOUT)
        send_notification_task.apply_async((request, notification.id))

    return True


#class CheckNotifications(Job):
#    run_every = 120 #seconds
#
#
#    def job(self):
#        check_notifications(HttpRequest())

#cronScheduler.register(CheckPassiveHosts)
#cronScheduler.register(CheckNotifications)
