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
import warnings
import logging

from django.conf import settings
from django.http import Http404
from django.core.cache import cache
from django.core.urlresolvers import resolve, Resolver404, reverse
from django.utils.http import urlquote
from django.shortcuts import get_object_or_404, redirect

from main.models import SiteConfig, AggregatedStatus, StatusSiteDomain

########
# REGEX
#TODO do we need this?
from settings import DOMAIN_SITE_CONFIG_CACHE_KEY, DOMAIN_AGGREGATION_CACHE_KEY

DOMAIN_RE = re.compile(r"(?P<domain>[\w\d_:\.-]+)/?(?P<tail>.*)")


class SiteConfigMiddleware(object):
    def process_request(self, request):
        domain = request.get_host()

        request.site_config = None
        request.aggregation = None

        if domain:
            site_config, public = SiteConfig.get_from_domain(domain)
            if site_config:
                request.urlconf = 'urls'
            else:
                if not site_config and request.path.startswith('/sites'):
                    view = resolve(request.path)
                    site_config_slug = view.kwargs.get('site_slug')
                    site_config = SiteConfig.objects.filter(slug=site_config_slug)
                    if site_config:
                        site_config = site_config[0]
                        public = site_config.public_internal_url

            if not public and site_config and not request.path.startswith(reverse("auth_login")):
                # require authentication for private status site
                if not request.user.is_authenticated():
                    return redirect("auth_login")

                # hide status site from other users
                if not site_config or site_config.user != request.user:
                    raise Http404

            #always show the user the private view
            if request.user.is_authenticated() and request.user == site_config.user:
                public = False

            request.site_config = site_config
            request.public = public

            aggregation = cache.get(DOMAIN_AGGREGATION_CACHE_KEY % domain, False)
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

                cache.set(DOMAIN_AGGREGATION_CACHE_KEY % domain, request.aggregation, 60)
                request.aggregation = aggregation
