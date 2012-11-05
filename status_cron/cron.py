#!/usr/bin/env python
# -*- coding: utf-8 -*-
##
## Authors: Adriano Marques <adriano@umitproject.org>
##          Alin Predoi <predoialin@gmail.com>
##
## Copyright (C) 2012 S2S Network Consultoria e Tecnologia da Informacao LTDA
##
## This program is free software: you can redistribute it and/or modify
## it under the terms of the GNU Affero General Public License as
## published by the Free Software Foundation, either version 3 of the
## License, or (at your option) any later version.
##
## This program is distributed in the hope that it will be useful,
## but WITHOUT ANY WARRANTY; without even the implied warranty of
## MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
## GNU Affero General Public License for more details.
##
## You should have received a copy of the GNU Affero General Public License
## along with this program.  If not, see <http://www.gnu.org/licenses/>.
##


import logging
import urllib2

from django.http import HttpRequest
from django.conf import settings

from celery import task
from celery.task.schedules import crontab
from celery.decorators import periodic_task
from main.memcache import memcache
from settings import CELERY_CACHE_TIMEOUT


CHECK_HOST_KEY = 'check_passive_host_%s'
CHECK_NOTIFICATION_KEY = 'check_notification_%s'

__author__ = 'apredoi,adrianomarques'

from status_cron.views import check_passive_url_task,check_passive_port_task,send_notification_task
from main.models import Module, Notification



@periodic_task(run_every=crontab(hour="*", minute="*/1", day_of_week="*"))
def inform_self_status():
    """This adds the ability to celery to send its own status to site-status
    as an active agent.
    """
    if settings.INFORM_SELF_STATUS:
        api_url = "%(STATUS_URL)s/api/report_status?module_id=%(STATUS_MODULE_ID)s&module_api=%(STATUS_API_KEY)s&module_secret=%(STATUS_API_SECRET)s&module_status=%(AGENT_STATUS)s"
        api_url %= dict(STATUS_URL=settings.INFORM_SELF_STATUS_URL,
                        STATUS_MODULE_ID=settings.INFORM_SELF_STATUS_MODULE_ID,
                        STATUS_API_KEY=settings.INFORM_SELF_STATUS_API_KEY,
                        STATUS_API_SECRET=settings.INFORM_SELF_STATUS_API_SECRET,
                        AGENT_STATUS="on-line")
        logging.info("Making status call with url %s" % api_url)
        agent_update = urllib2.urlopen(api_url)
        logging.info("Response from server after reporting self status: %s" % agent_update.read())
        logging.info("Done reporting self status.")
    else:
        logging.info("Inform self status is disabled.")


@periodic_task(run_every=crontab(hour="*", minute="*/1", day_of_week="*"))
def check_passive_url_monitors():
    request = HttpRequest()
    request.META['HTTP_X_CELERY_CRON'] = 'true'

    modules = Module.objects.filter(module_type='url_check')
    
    sending_modules = []
    for i in xrange(len(modules)):
        module = modules[i]

        passive_key = CHECK_HOST_KEY % module.id
        if memcache.get(passive_key,False):
            #this means that the check is still running for this module
            logging.critical("Module id %s is still running" % module.id)
            continue

        memcache.set(passive_key, module, CELERY_CACHE_TIMEOUT)

        sending_modules.append(module.id)
        if (i != 0 or len(modules) == 1) and (((i % settings.PASSIVE_URL_CHECK_BATCH) == 0) or (i == (len(modules) - 1))):
            # Don't run when it is the first iteration, unless only one module to monitor
            # Run in batch sizes defined by the settings and run the remaning at the end of
            # the loop even if batch size isn't met.
            check_passive_url_task.apply_async((request, sending_modules))
            sending_modules = []

    return True


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
