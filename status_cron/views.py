#!/usr/bin/env python
# -*- coding: utf-8 -*-
##
## Author: Adriano Monteiro Marques <adriano@umitproject.org>
##
## Copyright (C) 2011 S2S Network Consultoria e Tecnologia da Informacao LTDA
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
from logging.handlers import TimedRotatingFileHandler

import urllib2
import datetime
import logging
import uuid
import traceback
import itertools
from django.core.mail import send_mail, EmailMessage

from django.http import HttpResponse, Http404
from django.conf import settings

# Appengine TASKS
from main.models import *
from main.memcache import memcache
from main.decorators import staff_member_required

################
# Memcache Keys
CHECK_HOST_KEY = 'check_passive_host_%s'
CHECK_NOTIFICATION_KEY = 'check_notification_%s'

from djcelery import celery
from celery.exceptions import SoftTimeLimitExceeded

from logging.handlers import TimedRotatingFileHandler
from settings import LOGGING,MONITOR_LOG_PATH
import os
from dbextra.utils import ModuleListFieldHandler
MONITOR_LOG_SEPARATOR = ' '


def get_monitor_log(module_id):
    logger = logging.getLogger("rotating_logger")
    log_handler = ModuleListFieldHandler(module_id)
    logger.addHandler(log_handler)
    return logger

def debug(logger, msg=""):
    debug_tokens = (str(datetime.datetime.now()), )
    if isinstance(msg, tuple):
        debug_tokens += msg
    else:
        debug_tokens += (msg, )
    logger.debug(MONITOR_LOG_SEPARATOR.join(debug_tokens))



@celery.task(ignore_result=True)
@staff_member_required
def send_notification_task(request, notification_id):
    """This task will send out the notifications
    """
    notification = Notification.objects.get(pk=notification_id)
    notification.build_email_data()

    email = EmailMessage(subject=notification.subject,
                         body=notification.body,
                         to=[notification.site_config.notification_to,],
                         bcc=notification.list_emails,
                         headers = {'Reply-To': notification.site_config.notification_reply_to})

    sent = email.send()

    notification.sent_at = datetime.datetime.now()
    notification.save()
    
    memcache.delete(CHECK_NOTIFICATION_KEY % notification.id)
    return HttpResponse("OK")

@staff_member_required
def check_notifications_task(request, one_time, notification_queue_id):
    """This task will actually send out the notifications.
    """
    pass


def _create_new_event(module, status, down_at, back_at=None, details=""):
    event = ModuleEvent()
    event.down_at = down_at
    event.back_at = back_at
    event.status = status
    event.module = module
    event.details = details
    event.site_config = module.site_config
    event.save()


@celery.task(ignore_result=True, soft_timeout=50)
@staff_member_required
def check_passive_hosts_task(request, module_key):
    logger = get_monitor_log(module_key)
    debug(logger, ("begin",))


    module = Module.objects.get(id=module_key)
    events = ModuleEvent.objects.filter(module=module).filter(back_at=None)

    start = datetime.datetime.now()

    try:
        status_code = _get_status_code(module)
        end = datetime.datetime.now()

        total_time = end - start

        debug(logger, ("end", str(total_time.total_seconds()),))
        if total_time.seconds > 3:
        # TODO: Turn this into a notification
        #            logging.warning('Spent %s seconds checking %s' % (total_time.seconds, module.name))
            debug(logger,'Spent %s seconds checking %s' % (total_time.seconds, module.name))

        if status_code == 200:
            # This case is for when a module's status is set by hand and no event is created.
            if module.status != 'on-line' and not events:
                _create_new_event(module,"unknown", start, start)

            now = datetime.datetime.now()
            for event in events:
                event.back_at = now
                event.save()
                debug(logger,"Site is back online %s" % module.name)


    except SoftTimeLimitExceeded, e:
        details = '''%s %s
%s
---
%s
---
Events: %s''' % ("urlfetch.HTTPError", module.name, e,
                 traceback.extract_stack(), events)

        debug(logger, "time_limit_exceeded")

        if not events:
            _create_new_event(module, "off-line", start, None, details)

    except urllib2.HTTPError, e:
        details = '''%s %s
%s
---
%s
---
Events: %s''' % ("urlfetch.HTTPError", module.name, e,
                 traceback.extract_stack(), events)

        debug(logger, "http_error")

        if not events:
            _create_new_event(module, "unknown", start, None, details)

    except urllib2.URLError, e:
        details = '''%s %s
%s
---
%s
---
Events: %s''' % ("urllib2.URLError", module.name, e,
                 traceback.extract_stack(), events)

        debug(logger, "url_error")
        logging.critical("Events: %s" % events)
        if not events:
            _create_new_event(module, "off-line", start, None, details)

    except Exception, e:
        details = '''%s %s
%s
---
%s
---
Events: %s''' % ("Exception", module.name, e,
                 traceback.extract_stack(), events)
        debug(logger, "monitor_error")
        if not events:
            _create_new_event(module, "unknown", start, None, details)

    memcache.delete(CHECK_HOST_KEY % module.id)
    return HttpResponse("OK")

def _get_status_code(module):
    if settings.GAE:
        result = urlfetch.fetch(module.url,
                                follow_redirects=True,
                                allow_truncated=True,
                                deadline=60)
        return result.status_code
    result = urllib2.urlopen(module.url)
    return result.getcode()

@staff_member_required
def aggregate_daily_status(request):
    for module in Module.objects.all():
        module.today_status
    return HttpResponse("OK")
