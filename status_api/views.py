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
from django.views.decorators.csrf import csrf_exempt


from main.models import *

from status_api.decorators import authenticate_api_request
from settings import ACTIVE_MONITOR_THROTTLE_TIME, ACTIVE_MONITOR_CACHE_KEY
from django.core.cache import cache


def __build_response(**kwargs):
    return HttpResponse(json.dumps(kwargs))

def __known_status(status):
    for s in STATUS:
        if status in s:
            return True
    return False

@csrf_exempt
@authenticate_api_request
def report_status(request):
    status = request.POST.get('module_status', 'unknown')

    module_id = cache.get(ACTIVE_MONITOR_CACHE_KEY%request.module.id, False)

    if module_id:
        return __build_response(response="DENIED")

    cache.set(ACTIVE_MONITOR_CACHE_KEY%request.module.id, 'true', ACTIVE_MONITOR_THROTTLE_TIME)

    # check if the sent status is a known one
    if not __known_status(status):
        status = "unknown"

    new = False
    
    module = request.module
    module.updated_at = datetime.datetime.now()
    module.save()

    start = datetime.datetime.now()
    event = ModuleEvent.objects.filter(module=module, back_at=None)

    if not event:
        ev = ModuleEvent()
        ev.module = module
        new = True
        event = [ev,]

    for ev in event:
        if status != 'on-line':
            ev.down_at = start
            ev.status = status
        else:
            ev.back_at = start
            ev.down_at = start
        ev.save()
    
    return __build_response(response='OK',
                            new=new)

@csrf_exempt
@authenticate_api_request
def check_status(request):
    return __build_response(response='OK',
                            module=request.module.id,
                            status=request.module.status)

@csrf_exempt
@authenticate_api_request
def check_downtime(request):
    return __build_response(response='OK',
                            module=request.module.id,
                            downtime=request.module.total_downtime)

@csrf_exempt
@authenticate_api_request
def check_incidents(request):
    return __build_response(response='OK',
                            module=request.module.id,
                            incidents=module.last_incidents)

@csrf_exempt
@authenticate_api_request
def check_uptime(request):
    return __build_response(response='OK',
                            module=request.module.id,
                            incidents=module.last_uptime)

@csrf_exempt
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