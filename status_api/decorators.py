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


from django.http import HttpResponse, Http404
from django.utils import simplejson as json

from main.models import Module

def authenticate_api_request(view):
    def new_view(request, *args, **kwargs):
        api = request.REQUEST.get('module_api', None)
        secret = request.REQUEST.get('module_secret', None)
        module = request.REQUEST.get('module_id', None)
        
        if None in [api, secret, module]:
            return HttpResponse(json.dumps(dict(response='FAIL',
                                                reason='You must provide a module, api key and api secret. Check your settings file.')))
        
        module = Module.objects.filter(pk=module)
        if module:
            module = module[0]
            if module.authenticate(api, secret):
                request.module = module
                try:
                    return view(request, *args, **kwargs)
                except Exception, e:
                    return HttpResponse(json.dumps(dict(response='FAIL',
                                                        reason=str(e))))
        
        return HttpResponse(json.dumps(dict(response='FAIL',
                                            reason='Authentication failed.')))
    return new_view