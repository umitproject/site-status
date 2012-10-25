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

import pycurl
import datetime
import logging
import uuid
import traceback
import itertools
import cStringIO
from django.core.mail import send_mail, EmailMessage
from django.db import transaction

from django.http import HttpResponse, Http404
from django.conf import settings

from nmap import PortScanner

# Appengine TASKS
import re
from main.models import *
from main.memcache import memcache
from main.decorators import staff_member_required

################
# Memcache Keys
CHECK_HOST_KEY = 'check_passive_host_%s'
CHECK_NOTIFICATION_KEY = 'check_notification_%s'

from djcelery import celery
from celery.exceptions import SoftTimeLimitExceeded

from settings import NMAP_ARGS, CURL_TIMEOUT_LIMIT
import os
from dbextra.utils import ModuleListFieldHandler, MAX_LOG_ENTRIES

MONITOR_LOG_SEPARATOR = ' '



class RegexDoesntMatch(Exception):
    def __init__(self, value):
        self.value = value
    def __str__(self):
        return repr(self.value)


class StatusCodeDoesntMatch(Exception):
    def __init__(self, value):
        self.value = value
    def __str__(self):
        return repr(self.value)


def debug(module, msg=""):
    module.append_log(msg)

@celery.task(ignore_result=True)
@staff_member_required
@transaction.commit_manually
def send_notification_task(request, notification_id):
    """This task will send out the notifications
    """
    notification = Notification.objects.get(pk=notification_id)
    try:
        notification.build_email_data()

        email = EmailMessage(subject=notification.subject,
                             body=notification.body,
                             to=[notification.site_config.notification_to,],
                             bcc=notification.list_emails,
                             headers = {'Reply-To': notification.site_config.notification_reply_to})

        sent = email.send()

        notification.sent_at = datetime.datetime.now()
        notification.send = False
        notification.save()
    except Exception, err:
        logging.critical("Error while trying to send notification [%s] - (%s)" % (notification, err))

    transaction.commit()
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


@celery.task(ignore_result=True)
@staff_member_required
@transaction.commit_manually
def check_passive_url_task(request, module_key):
    module = Module.objects.get(id=module_key)
    events = ModuleEvent.objects.filter(module=module).filter(back_at=None)
    debug(module, ("begin",))

    start = datetime.datetime.now()

    try:
        remote_response = _get_remote_response(module)
        end = datetime.datetime.now()

        total_time = end - start

        debug(module, ("end_check", str(total_time.total_seconds()),))
        if total_time.seconds > 3:
        # TODO: Turn this into a notification
        #            logging.warning('Spent %s seconds checking %s' % (total_time.seconds, module.name))
            debug(module,'Spent %s seconds checking %s' % (total_time.seconds, module.name))

        if _check_status_code(module,remote_response) and _check_keyword(module,remote_response):

            # This case is for when a module's status is set by hand and no event is created.
            if module.status != 'on-line' and not events:
                _create_new_event(module,"unknown", start, start)

            now = datetime.datetime.now()
            for event in events:
                event.back_at = now
                event.save()
                debug(module,"Site is back online %s" % module.name)


    except SoftTimeLimitExceeded, e:
        details = '''%s %s
%s
---
%s
---
Events: %s''' % ("urlfetch.HTTPError", module.name, e,
                 traceback.extract_stack(), events)

        debug(module, "[%s] time_limit_exceeded"%module.id)
        transaction.rollback() #cancel saving events if it exceeded timeout

        if not events:
            _create_new_event(module, "off-line", start, None, details)


    except pycurl.error, e:
        details = '''%s %s
%s
---
%s
---
Events: %s''' % ("pycurl_error", module.name, e,
                 traceback.extract_stack(), events)

        debug(module, "url_error (%s) %s"%(e[0],e[1]))
        logging.critical("Events: %s" % events)
        if not events:
            _create_new_event(module, "off-line", start, None, details)

    except (RegexDoesntMatch, StatusCodeDoesntMatch) as e:
        details = '''%s %s
%s
---
%s
---
Events: %s''' % ("pycurl_error", module.name, e,
                 traceback.extract_stack(), events)

        debug(module, "matching_error: %s"%e)
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
        debug(module, "monitor_error%s"%details)
        if not events:
            _create_new_event(module, "unknown", start, None, details)
    finally:
        debug(module, "end task")
        transaction.commit()
        memcache.delete(CHECK_HOST_KEY % module.id)
    return HttpResponse("OK")


@celery.task(ignore_result=True)
@staff_member_required
@transaction.commit_manually
def check_passive_port_task(request, module_key):

    module = Module.objects.get(id=module_key)
    debug(module, ("begin",))
    events = ModuleEvent.objects.filter(module=module).filter(back_at=None)

    portscanner = PortScanner()
    result = None
    try:
        if not module.check_port:
            raise Exception("Improperly configured")
        portscanner.scan(arguments = NMAP_ARGS, ports=str(module.check_port), hosts=module.host.encode('ascii','ignore'))

        now = datetime.datetime.now()

        host = portscanner.all_hosts()[0]
        if 'open' == portscanner[host]['tcp'][module.check_port]['state']:
            debug(module, "Port open")
            for event in events:
                event.back_at = now
                event.save()
                debug(module,"Site is back online %s" % module.name)
        else:
            if not events:
                _create_new_event(module, "off-line", now, None, "Port is closed")

    except KeyError, e:
        pass

    except Exception, e:
        details = '''%s %s
%s
---
%s
---
Events: %s''' % ("Exception", module.name, e,
                 traceback.extract_stack(), events)
        debug(module, "monitor_error" + details)
        start = datetime.datetime.now()
        if not events:
            _create_new_event(module, "unknown", start, None, details)


    finally:
        debug(module, "end task")
        transaction.commit()
        memcache.delete(CHECK_HOST_KEY % module.id)
    return HttpResponse("OK")

def _get_remote_response(module):
    try:
        print "[%s] calling %s"%(module.id, module.url)
        curl = pycurl.Curl()
        buff = cStringIO.StringIO()
        hdr = cStringIO.StringIO()

        curl.setopt(pycurl.URL, module.url.encode('utf-8'))
        curl.setopt(pycurl.WRITEFUNCTION, buff.write)
        curl.setopt(pycurl.HEADERFUNCTION, hdr.write)
        curl.setopt(pycurl.FAILONERROR, 1 if module.fail_on_error else 0)
        curl.setopt(pycurl.FOLLOWLOCATION, 1 if module.follow_location else 0)
        curl.setopt(pycurl.TIMEOUT, CURL_TIMEOUT_LIMIT)

        curl.perform()

        print "[%s] end calling %s"%(module.id, module.url)

        return dict({'http_code':curl.getinfo(pycurl.HTTP_CODE), 'http_headers': hdr.getvalue(), 'http_response': buff.getvalue()})
    except Exception, e:
        raise e

def _check_status_code(module,remote_response):
    expected_status = module.expected_status or 200
    actual_status = remote_response.get('http_code', 0)
    if actual_status != expected_status:
        raise StatusCodeDoesntMatch("Expected %s status but found %s instead"%(expected_status, actual_status))
    return True

def _check_keyword(module,remote_response):
    if module.search_keyword and not re.search(module.search_keyword, remote_response.get('http_response', '')):
        raise RegexDoesntMatch("%s doesn't match the response body"%module.search_keyword)
    return True

@staff_member_required
def aggregate_daily_status(request):
    for module in Module.objects.all():
        module.today_status
    return HttpResponse("OK")
