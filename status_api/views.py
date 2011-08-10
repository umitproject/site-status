#!/usr/bin/env python
import urllib2

from django.http import HttpResponse, Http404

from main.models import *

from status_api.decorators import authenticate_api_request

@authenticate_api_request
def report_status(request):
    status = request.POST['module_status']
    
    module = request.module
    module.updated_at = datetime.datetime.now()
    module.save()
        
    if status != 'online':
        event = ModuleEvent.objects.get_or_create()
        event.down_at = datetime.datetime.now()
        event.status = status
        event.module = module
        event.save()
    
    return HttpResponse('OK')

def check_status(request):
    pass

def check_incidents(request):
    pass

def check_uptime(request):
    pass

def check_availability(request):
    pass


###################################
# Future:
# - Schedule Maintenance
# - Send notification
# - Set site message
# - Disable/Enable monitored module
###################################