#!/usr/bin/env python
import urllib2
import datetime

from django.http import HttpResponse, Http404

from main.models import *

def check_passive_hosts(request):
    modules = Module.objects.filter(module_type='passive')
    for module in modules:
        try:
            events = ModuleEvent.objects.filter(module=module).filter(back_at=None)
            
            result = urllib2.urlopen(module.url)
            if result.getcode() == 200:
                now = datetime.datetime.now() 
                for event in events:
                    event.back_at = now
                    event.save()
            
            elif result.getcode() == 404:
                if not events:
                    event = ModuleEvent()
                    event.status = "off-line"
                    event.module = module
                    event.save()
                
        except urllib2.HTTPError, e:
            if not events:
                event = ModuleEvent()
                event.status = "unknown"
                event.module = module
                event.save()
                
        except urllib2.URLError, e:
            if not events:
                event = ModuleEvent()
                event.status = "off-line"
                event.module = module
                event.save()
        
        module.aggregate_daily_status()
    
    return HttpResponse("OK")

def aggregate_daily_status(request):
    modules = Module.objects.all()
    for module in modules:
        module.aggregate_daily_status()

    return HttpResponse('OK')
        

