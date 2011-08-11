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

import urllib2
import datetime
import logging
import uuid
import traceback
import itertools

from django.http import HttpResponse, Http404
from django.conf import settings

# Appengine TASKS
from google.appengine.api import taskqueue

from google.appengine.api import urlfetch

from main.models import *
from main.memcache import memcache
from main.decorators import staff_member_required
from main.utils import send_mail

################
# Memcache Keys
CHECK_HOST_KEY = 'check_passive_host_%s'
CHECK_NOTIFICATION_KEY = 'check_notification_%s'

@staff_member_required
def check_passive_hosts(request):
    modules = Module.objects.filter(module_type='passive')
    
    for module in modules:
        if memcache.get(CHECK_HOST_KEY % module.id, False):
            # This means that we still have a processing task for this host
            # TODO: Check if the amount of retries is too high, and if it is
            #       then create an event to sinalize that there is an issue
            #       with this host.
            logging.critical('Task %s is still processing...' % (CHECK_HOST_KEY % module.id))
            continue
        
        try:
            task_name = 'check_passive_host_%s_%s' % ("-".join(module.name.split(" ")).lower(), uuid.uuid4())
            task = taskqueue.add(url='/cron/check_passive_hosts_task/%s' % module.id,
                          name= task_name, queue_name='cron')
            memcache.set(CHECK_HOST_KEY % module.id, task)
            
            logging.info('Scheduled task %s' % task_name)
            
        except taskqueue.TaskAlreadyExistsError, e:
            logging.info('Task is still running for module %s: %s' % \
                 (module.name,'/cron/check_passive_hosts_task/%s' % module.id))
    
    return HttpResponse("OK")

@staff_member_required
def check_notifications(request):
    """This method calls out the tasks send notifications.
    Since it is a cron called view, there is a timeout, so we might want to
    make sure we never get more notifications than we can handle within that
    timeframe.
    """
    notifications = Notification.objects.filter(sent_at=None).order_by('-created_at')
    
    logging.info('>>> Checking %s notifications.' % len(notifications))
    
    for notification in notifications:
        # Create the notification queue
        not_key = CHECK_NOTIFICATION_KEY % notification.id
        if memcache.get(not_key, False):
            # This means that we still have a processing task for this host
            # TODO: Check if the amount of retries is too high, and if it is
            #       then create an event to sinalize that there is an issue
            #       with this host.
            logging.critical('Task %s is still processing...' %
                                (CHECK_NOTIFICATION_KEY % notification.id))
            continue
        
        try:
            task_name = 'check_notification_%s_%s' % (notification.id, uuid.uuid4())
            task = taskqueue.add(url='/cron/send_notification_task/%s' % notification.id,
                                 name= task_name, queue_name='cron')
            if task is None:
                logging.critical("!!!! TASK IS NONE! %s " % task_name)
            memcache.set(not_key, task)
            
        except taskqueue.TaskAlreadyExistsError, e:
            logging.info('Task is still running for module %s: %s' % \
                 (module.name,'/cron/create_notification_queue/%s' % notification.id))
    
    return HttpResponse("OK")

@staff_member_required
def send_notification_task(request, notification_id):
    """This task will send out the notifications
    """
    notification = Notification.objects.get(pk=notification_id)
    notification.build_email_data()
    
    sent = send_mail(notification.site_config.notification_sender,
                     notification.site_config.notification_to,
                     bcc=notification.list_emails,
                     reply_to=notification.site_config.notification_reply_to,
                     subject=notification.subject,
                     body=notification.body,
                     html=notification.html)
    
    notification.sent_at = datetime.datetime.now()
    notification.save()
    
    memcache.delete(CHECK_NOTIFICATION_KEY % notification.id)
    return HttpResponse("OK")

@staff_member_required
def check_notifications_task(request, one_time, notification_queue_id):
    """This task will actually send out the notifications.
    """
    pass

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
def check_passive_hosts_task(request, module_key):
    module = Module.objects.get(id=module_key)
    events = ModuleEvent.objects.filter(module=module).filter(back_at=None)
    
    start = datetime.datetime.now()
    
    try:
        status_code = _get_status_code(module)
        end = datetime.datetime.now()
        
        total_time = end - start
        if total_time.seconds > 3:
            # TODO: Turn this into a notification
            logging.warning('Spent %s seconds checking %s' % (total_time.seconds, module.name))
        
        if status_code == 200:
            # This case is for when a module's status is set by hand and no event is created.
            if module.status != 'on-line' and not events:
                event = ModuleEvent()
                event.down_at = start
                event.back_at = start
                event.status = "unknown"
                event.module = module
                event.site_config = module.site_config
                event.save()
            
            now = datetime.datetime.now() 
            for event in events:
                event.back_at = now
                event.save()
                logging.info("Site is back online %s" % module.name)
    
    except urllib2.HTTPError, e:
        details = '''%s %s
%s
---
%s
---
Events: %s''' % ("urlfetch.HTTPError", module.name, e,
                 traceback.extract_stack(), events)
        
        if not events:
            event = ModuleEvent()
            event.down_at = start
            event.status = "unknown"
            event.module = module
            event.details = details
            event.site_config = module.site_config
            event.save()
    
    except urllib2.URLError, e:
        details = '''%s %s
%s
---
%s
---
Events: %s''' % ("urllib2.URLError", module.name, e,
                 traceback.extract_stack(), events)
        
        logging.critical("Events: %s" % events)
        if not events:
            event = ModuleEvent()
            event.down_at = start
            event.status = "off-line"
            event.module = module
            event.details = details
            event.site_config = module.site_config
            event.save()
    
    except urlfetch.InvalidURLError, e:
        details = '''%s %s
%s
---
%s
---
Events: %s''' % ("urlfetch.InavlidURLError", module.name, e,
                 traceback.extract_stack(), events)

        if not events:
            event = ModuleEvent()
            event.down_at = start
            event.status = "unknown"
            event.module = module
            event.details = details
            event.site_config = module.site_config
            event.save()
    
    except urlfetch.DownloadError, e:
        details = '''%s %s
%s
---
%s
---
Events: %s''' % ("urlfetch.DownloadError", module.name, e,
                 traceback.extract_stack(), events)

        if not events:
            event = ModuleEvent()
            event.down_at = start
            event.status = "unknown"
            event.module = module
            event.details = details
            event.site_config = module.site_config
            event.save()
    
    except urlfetch.ResponseTooLargeError, e:
        details = '''%s %s
%s
---
%s
---
Events: %s''' % ("urlfetch.ResponseTooLargeError", module.name, e,
                 traceback.extract_stack(), events)

        if not events:
            event = ModuleEvent()
            event.down_at = start
            event.status = "unknown"
            event.module = module
            event.details = str(e)
            event.site_config = module.site_config
            event.save()
    
    except urlfetch.Error, e:
        details = '''%s %s
%s
---
%s
---
Events: %s''' % ("urlfetch.Error", module.name, e,
                 traceback.extract_stack(), events)

        if not events:
            event = ModuleEvent()
            event.down_at = start
            event.status = "unknown"
            event.module = module
            event.details = details
            event.site_config = module.site_config
            event.save()
    
    except Exception, e:
        details = '''%s %s
%s
---
%s
---
Events: %s''' % ("Exception", module.name, e,
                 traceback.extract_stack(), events)
        
        if not events:
            event = ModuleEvent()
            event.down_at = start
            event.status = "unknown"
            event.module = module
            event.details = details
            event.site_config = module.site_config
            event.save()
    
    memcache.delete(CHECK_HOST_KEY % module.id)
    return HttpResponse("OK")

@staff_member_required
def aggregate_daily_status(request):
    for module in Module.objects.all():
        module.today_status
    return HttpResponse("OK")
