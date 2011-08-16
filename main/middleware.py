#!/usr/bin/env python
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

import datetime
import re
import logging

from django.conf import settings
from django.http import Http404
from django.core.cache import cache
from django.core.urlresolvers import resolve, Resolver404
from django.utils.http import urlquote

from main.models import SiteConfig, AggregatedStatus, StatusSiteDomain

########
# REGEX
DOMAIN_RE = re.compile(r"(?P<domain>[\w\d_:\.-]+)/?(?P<tail>.*)")

############
# CACHE KEY
DOMAIN_SITE_CONFIG_CACHE_KEY = 'domain_site_config_%s'
DOMAIN_AGGREGATION_CACHE_KEY = 'domain_aggregation_%s'


class SiteConfigMiddleware(object):
    def process_request(self, request):
        domain_re = DOMAIN_RE.search(request.get_host())
        
        request.site_config = None
        request.aggregation = None
        
        if domain_re:
            domain = domain_re.groupdict()
            
            site_config = cache.get(DOMAIN_SITE_CONFIG_CACHE_KEY % domain['domain'], False)
            if site_config:
                request.site_config = site_config
            else:
                site_config = SiteConfig.get_from_domain(domain['domain'])
                
                if site_config:
                    request.site_config = site_config
                else:
                    site_config = SiteConfig()
                    site_config.site_name = domain['domain']
                    site_config.main_site_url = domain['domain']
                    site_config.save()
                    
                    status_domain = StatusSiteDomain()
                    status_domain.status_url = domain['domain']
                    status_domain.site_config = site_config
                    status_domain.save()
                    
                    request.site_config = site_config
            
            aggregation = cache.get(DOMAIN_AGGREGATION_CACHE_KEY % domain['domain'], False)
            if aggregation:
                request.aggregation = aggregation
            else:
                aggregation = AggregatedStatus.objects.filter(site_config=request.site_config)
                if not aggregation:
                    aggregation = AggregatedStatus()
                    aggregation.created_at = datetime.datetime.now()
                    aggregation.site_config = request.site_config
                    aggregation.save()
                else:
                    aggregation = aggregation[0]
                    
                request.aggregation = aggregation
            
            cache.set(DOMAIN_SITE_CONFIG_CACHE_KEY % domain['domain'], request.site_config, 120)
            cache.set(DOMAIN_AGGREGATION_CACHE_KEY % domain['domain'], request.aggregation, 60)
                
            
                