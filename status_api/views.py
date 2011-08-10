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

from django.http import HttpResponse, Http404
from django.utils import simplejson as json

from main.models import *

from status_api.decorators import authenticate_api_request

def __build_response(**kwargs):
    return HttpResponse(json.dumps(kwargs))

@authenticate_api_request
def report_status(request):
    status = request.POST['module_status']
    new = False
    
    module = request.module
    module.updated_at = datetime.datetime.now()
    module.save()
        
    event = ModuleEvent.objects.filter(module=module, back_at=None)
    if status != 'online':
        if not event:
            event = ModuleEvent()
            event.down_at = datetime.datetime.now()
            event.status = status
            event.module = module
            event.save()
            new = True
    else:
        event.back_at = datetime.datetime.now()
        event.save()
    
    return __build_response(response='OK',
                            new=new)

@authenticate_api_request
def check_status(request):
    return __build_response(response='OK',
                            module=request.module.id,
                            status=request.module.status)

def check_downtime(request):
    return __build_response(response='OK',
                            module=request.module.id,
                            downtime=request.module.total_downtime)

@authenticate_api_request
def check_incidents(request):
    return __build_response(response='OK',
                            module=request.module.id,
                            incidents=module.last_incidents)

@authenticate_api_request
def check_uptime(request):
    return __build_response(response='OK',
                            module=request.module.id,
                            incidents=module.last_uptime)

@authenticate_api_request
def check_availability(request):
    return __build_response(response='OK',
                            module=request.module.id,
                            incidents=module.availability)


###################################
# Future:
# - Schedule Maintenance
# - Send notification
# - Set site message
# - Disable/Enable monitored module
###################################