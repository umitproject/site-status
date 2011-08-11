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

import logging

from django.conf import settings

def get_settings(request):
    return {'GOOGLE_ANALYTICS_ID': request.site_config.analytics_id,
            'SITE_NAME': request.site_config.site_name,
            'MAIN_SITE_URL': request.site_config.main_site_url,
            'CONTACT_PHONE': request.site_config.contact_phone,
            'CONTACT_EMAIL': request.site_config.contact_email,
            'SHOW_INCIDENTS': request.site_config.show_incidents,
            'SHOW_UPTIME': request.site_config.show_uptime,
            'SHOW_LAST_INCIDENT': request.site_config.show_last_incident,
            'twitter_account': request.site_config.twitter_account,
            'site_config':request.site_config}