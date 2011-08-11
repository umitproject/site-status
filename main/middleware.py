

import datetime
import re
import logging

from django.conf import settings
from django.http import Http404

from django.core.urlresolvers import resolve, Resolver404
from django.utils.http import urlquote

from main.models import SiteConfig, AggregatedStatus

DOMAIN_RE = re.compile(r"(?P<domain>[\w\d_:\.-]+)/?(?P<tail>.*)")


class SiteConfigMiddleware(object):
    def process_request(self, request):
        domain_re = DOMAIN_RE.search(request.get_host())
        
        request.site_config = None
        request.aggregation = None
        
        if domain_re:
            domain = domain_re.groupdict()
            
            # TODO: Cache site_config to avoid calling datastore on every request
            #       cache is already being evicted on every save for the site_config.
            site_config = SiteConfig.objects.filter(status_url=domain['domain'])
            if site_config:
                request.site_config = site_config[0]
            else:
                site_config = SiteConfig()
                site_config.site_name = domain['domain']
                site_config.status_url = domain['domain']
                site_config.main_site_url = domain['domain']
                site_config.save()
                
                request.site_config = site_config
            
            aggregation = AggregatedStatus.objects.filter(site_config=request.site_config)
            if not aggregation:
                aggregation = AggregatedStatus()
                aggregation.created_at = datetime.datetime.now()
                aggregation.site_config = request.site_config
                aggregation.save()
            else:
                aggregation = aggregation[0]
                
            request.aggregation = aggregation
                
            
                