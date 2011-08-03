#!/usr/bin/env python

import random
import datetime
import urllib2
import logging

from django.shortcuts import render, render_to_response, get_object_or_404
from django.http import HttpResponse, Http404
from django.conf import settings
from django.contrib.auth.models import User
from django.utils import simplejson as json

from main.models import *


def home(request, msg=None):
    modules = Module.objects.all()
    show_days = Module.show_days()
    aggregation = AggregatedStatus.objects.all()[0]
    last_incident = aggregation.last_incident
    current_availability = aggregation.percentage_uptime
    
    incidents_data = json.dumps(aggregation.incidents_data)
    uptime_data = json.dumps(aggregation.uptime_data)
    
    context = locals()
    if msg is not None:
        context['msg'] = msg
    return render(request, 'home.html', context)

def event(request, event_id):
    # TODO: Must show event details
    event = get_object_or_404(ModuleEvent, pk=event_id)
    scheduled_maintenances = ScheduledMaintenance.objects.filter(module=event.module)
    
    context = locals()
    return render(request, 'event.html', context)
    

def subscribe(request, event_id=None, module_id=None):
    """Possible behaviors:
    
    1 - If no id is provided
      - We show the full form, and let user decide whether he want to remain
        subscribed to receive whatever status for this system or receive a
        one time notification once this system have recovered from current
        disruption.
    2 - If event_id is provided
      - We show the full form, and let user decide whether he want to remain
        subscribed to receive whatever status for this event or receive a
        one time notification once this event have recovered from current
        disruption. If event is recovered, let user subscribe to the module
        instead and don't show one-time option.
    3 - If module_id is provided
      - We show the full form, and let user decide whether he want to remain
        subscribed to receive whatever status for this module or receive a
        one time notification once this module have recovered from current
        disruption. If module is online, let user subscribe to the module
        instead and don't show one-time option.
    """
    system = False
    module = False
    event = False
    one_time = False
    
    if (event_id is None) and (module_id is None):
        system = True
    elif (event_id is not None) and (module_id is None):
        pass
    
    context = locals()
    return render(request, 'subscribe.html', context)


def _create_fake_events(module, range_days):
    today = datetime.datetime.now()
    time = today - datetime.timedelta(days=range_days)
    events = []
    for i in xrange(range_days):
        for j in xrange(random.randrange(1, 24, 1)):
            event = ModuleEvent()
            event.status = random.choice(STATUS)[0]
            event.module = module
            event.down_at = time
            event.back_at = time + datetime.timedelta(minutes=random.randrange(1, 60, 2))
            event.save()
            
            events.append(event)
        
        time = time + datetime.timedelta(days=1)

def _create_fake_module(name, description, module_type, host, url):
    range_days = 7
    
    mod = Module()
    mod.name = name
    mod.description = description
    mod.module_type = module_type
    mod.host = host
    mod.url = url
    mod.status = 'on-line'
    mod.save()
    
    _create_fake_events(mod, range_days)
    
    
def test_populate(request):
    if settings.DEBUG:
        if not Module.objects.filter(name="Umit Project"):
            _create_fake_module("Umit Project",
                                "This is our main website.",
                                "passive",
                                "www.umitproject.org",
                                "http://www.umitproject.org")
        
        if not Module.objects.filter(name="Trac"):
            _create_fake_module("Trac",
                                "This is our old development site, based on Trac.",
                                "passive",
                                "trac.umitproject.org",
                                "http://trac.umitproject.org")
        
        if not Module.objects.filter(name="Redmine"):
            _create_fake_module("Redmine",
                                "This is our new development site, based on Redmine.",
                                "passive",
                                "dev.umitproject.org",
                                "http://dev.umitproject.org")
        
        if not Module.objects.filter(name="Git"):
            _create_fake_module("Git",
                                "This is our git repository.",
                                "passive",
                                "git.umitproject.org",
                                "http://git.umitproject.org")
        
        if not Module.objects.filter(name="Blog"):
            _create_fake_module("Blog",
                                "This is our blog.",
                                "passive",
                                "blog.umitproject.org",
                                "http://blog.umitproject.org")
        
        # Create test user
        if not User.objects.filter(username='admin'):
            user = User.objects.create_user('admin', 'adriano@umitproject.org', 'test')
            user.is_staff = True
            user.is_superuser = True
            user.is_active = True
            user.save()
        
        # Create Twitter Account
        if not TwitterAccount.objects.filter(login='umit_project'):
            twitter_account = TwitterAccount()
            twitter_account.login = 'umit_project'
            twitter_account.api_key = ''
            twitter_account.api_secret = ''
            twitter_account.post_tweet_automatically = True
            twitter_account.monitor_stream = True
            twitter_account.monitor_stream_terms = ''
            twitter_account.save()
        
        return home(request, 'Test Populate OK')
    
    raise Http404

def test_events_and_aggregations(request):
    modules = Module.objects.all()
    logging.critical('Creating fake events... %s' % modules)
    for module in modules:
        logging.critical('Creating fake events for %s' % module)
        _create_fake_events(module, 7)
    
    return home(request, 'Test Events and Aggregations OK')

def clean_cache(request):
    msg = ''
    if memcache.flush_all():
        msg = 'Flush cache OK'
    else:
        msg = 'Flush cache FAILED'
    return home(request, msg)

def hard_reset(request):
    [m.delete() for m in Module.objects.all()]
    [e.delete() for e in ModuleEvent.objects.all()]
    [d.delete() for d in DailyModuleStatus.objects.all()]
    
    memcache.flush_all()
    
    return home(request, 'Flush cache FAILED') 
    
