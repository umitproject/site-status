#!/usr/bin/env python
import urllib2

from django.http import HttpResponse, Http404

from main.models import *
from main.decorators import login_required

@login_required
def save_active_host_status(request):
    status = request.POST['module_status']
    api = request.POST['module_api']
    secret = request.POST['module_secret']
    module = request.POST['module']
    
    module = Module.objects.get(name=module)
    if module.authenticate(api, secret):
        module.save() # This is in order to mark when was last updated
        
        if status != 'online':
            event = ModuleEvent()
            event.status = status
            event.module = module
            event.save()
        else:
            return HttpResponse('OK')
    
    raise Http404