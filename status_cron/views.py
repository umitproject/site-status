#!/usr/bin/env python
import urllib2
import datetime
import logging
import uuid
import traceback

from django.http import HttpResponse, Http404
from django.conf import settings

# Appengine TASKS
from google.appengine.api import taskqueue

from google.appengine.api import urlfetch

from main.models import *
from main.memcache import memcache
from main.decorators import staff_member_required

################
# Memcache Keys
CHECK_HOST_KEY = 'check_passive_host_%s'

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
            memcache.set(CHECK_HOST_KEY % module.id, task, 60)
            
            logging.info('Scheduled task %s' % task_name)
            
        except taskqueue.TaskAlreadyExistsError, e:
            logging.info('Task is still running for module %s: %s' % \
                 (module.name,'/cron/check_passive_hosts_task/%s' % module.id))
    
    return HttpResponse("OK")

@staff_member_required
def check_notifications(request):
    """This method calls out the tasks to create notification queues.
    Since it is a cron called view, there is a timeout, so we might want to
    make sure we never get more notifications than we can handle within that
    timeframe.
    """
    notifications = Notification.objects.filter(sent_at=None)
    for notification in notifications:
        # Create the notification queue
        pass

@staff_member_required
def create_notification_queue(request, one_time, notification_queue_id):
    """This task will actually send out the notifications.
    """
    pass

@staff_member_required
def check_notifications_task(request, one_time, notification_queue_id):
    """This task will actually send out the notifications.
    """
    pass

def _get_status_code(module):
    if settings.GAE:
        result = urlfetch.fetch(module.url)
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
                event.save()
            
            now = datetime.datetime.now() 
            for event in events:
                event.back_at = now
                event.save()
                logging.info("Site is back online %s" % module.name)
    
    except urllib2.HTTPError, e:
        logging.critical("urlfetch.HTTPError %s" % module.name)
        logging.critical(e)
        logging.critical(traceback.extract_stack())
        logging.critical("Events: %s" % events)
        
        if not events:
            event = ModuleEvent()
            event.down_at = start
            event.status = "unknown"
            event.module = module
            event.details = str(e)
            event.save()
    
    except urllib2.URLError, e:
        logging.critical("Events: %s" % events)
        if not events:
            event = ModuleEvent()
            event.down_at = start
            event.status = "off-line"
            event.module = module
            event.details = str(e)
            event.save()
    
    except urlfetch.InvalidURLError, e:
        logging.critical("urlfetch.InvalidURLError %s" % module.name)
        logging.critical(e)
        logging.critical(traceback.extract_stack())
        logging.critical("Events: %s" % events)
        
        if not events:
            event = ModuleEvent()
            event.down_at = start
            event.status = "unknown"
            event.module = module
            event.details = str(e)
            event.save()
    
    except urlfetch.DownloadError, e:
        logging.critical("urlfetch.DownloadError %s" % module.name)
        logging.critical(e)
        logging.critical(traceback.extract_stack())
        logging.critical("Events: %s" % events)
        
        if not events:
            event = ModuleEvent()
            event.down_at = start
            event.status = "unknown"
            event.module = module
            event.details = str(e)
            event.save()
    
    except urlfetch.ResponseTooLargeError, e:
        logging.critical("urlfetch.ResponseTooLargeError %s" % module.name)
        logging.critical(e)
        logging.critical(traceback.extract_stack())
        logging.critical("Events: %s" % events)
        
        if not events:
            event = ModuleEvent()
            event.down_at = start
            event.status = "unknown"
            event.module = module
            event.details = str(e)
            event.save()
    
    except urlfetch.Error, e:
        logging.critical("urlfetch.Error %s" % module.name)
        logging.critical(e)
        logging.critical(traceback.extract_stack())
        logging.critical("Events: %s" % events)
        
        if not events:
            event = ModuleEvent()
            event.down_at = start
            event.status = "unknown"
            event.module = module
            event.details = str(e)
            event.save()
    
    except Exception, e:
        logging.critical("Error while executing check for %s" % module.name)
        logging.critical(e)
        logging.critical(traceback.extract_stack())
        logging.critical("Events: %s" % events)
        
        if not events:
            event = ModuleEvent()
            event.down_at = start
            event.status = "unknown"
            event.module = module
            event.details = str(e)
            event.save()
    
    memcache.delete(CHECK_HOST_KEY % module.id)
    return HttpResponse("OK")

@staff_member_required
def aggregate_daily_status(request):
    for module in Module.objects.all():
        module.today_status
    return HttpResponse("OK")
