#!/usr/bin/env python

import random
import datetime
import urllib2

from django.shortcuts import render_to_response
from django.http import HttpResponse, Http404
from django.conf import settings
from django.contrib.auth.models import User

from main.models import *


def home(request):
    modules = Module.objects.all()
    
    context = locals()
    return render_to_response('home.html', context)

def subscribe(request):
    context = locals()
    return render_to_response('subscribe.html', context)


def _create_fake_events(module, range_days):
    today = datetime.datetime.now()
    time = today - datetime.timedelta(days=range_days)
    events = []
    for i in xrange(range_days):
        for j in xrange(random.randrange(1, 10, 1)):
            event = ModuleEvent()
            event.status = random.choice(STATUS)[0]
            event.module = module
            event.down_at = time
            event.back_at = time + datetime.timedelta(minutes=random.randrange(1, 120, 2))
            event.save()
            
            events.append(event)
        
        module.aggregate_daily_status(time, events)
        
        time = time + datetime.timedelta(days=1)

def _create_fake_module(name, description, module_type, host, url):
    range_days = 30
    
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
        user = User.objects.create_user('admin', 'adriano@umitproject.org', 'test')
        user.is_staff = True
        user.is_superuser = True
        user.is_active = True
        user.save()
        
        context = locals()
        context['msg'] = 'Test Populate OK'
        return render_to_response('home.html', context)
    
    raise Http404
