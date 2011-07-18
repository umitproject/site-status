#!/usr/bin/env python
import urllib2

from django.http import HttpResponse, Http404

from main.models import *

def check_passive_hosts(request):
    modules = Module.objects.filter(module_type='passive')
    for module in modules:
        try:
            result = urllib2.urlopen(module.url)
            if result.getcode() == 200:
                module.status = 'on-line'
                module.save()
        except urllib2.HTTPError, e:
            if module.status != 'on-line':
                event = ModuleEvent()
                event.status = "unknown"
                event.module = module
                event.save()
        except urllib2.URLError, e:
            if module.status != 'on-line':
                event = ModuleEvent()
                event.status = "offline"
                event.module = module
                event.save()
    return HttpResponse("OK")
        
        

