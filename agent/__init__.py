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
from urllib import urlencode

from django.utils import simplejson as json

import logging

from agent import settings

def call(method, **kwargs):
    url =  '%s/%s' % (settings.API_URL, method)
    kwargs.update(dict(module_api=settings.API_KEY,
                       module_secret=settings.API_SECRET,
                       module_id=settings.MODULE_ID))
    response = urllib2.urlopen(url, urlencode(kwargs))
    
    logging.info('>>> Response info from %s: %s' % (url, response.info()))
    
    response = response.read()
    
    try:
        response = json.loads(response)
    except Exception, e:
        response = dict(response='FAIL', reason="%s - %s" % (response, str(e)))
    
    return response

def test_url(url, re):
    try:
        response = urllib2.urlopen(url)
        
        logging.info('>>> Response info from %s: %s' % (url, response.info()))
        
        assert re.match(response.read())
        
        return True
    except:
        return False