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

from main.models import twitter_account

def get_settings(request):
    return {'GOOGLE_ANALYTICS_ID': settings.GOOGLE_ANALYTICS_ID,
            'SITE_NAME': settings.SITE_NAME,
            'MAIN_SITE_URL': settings.MAIN_SITE_URL,
            'CONTACT_PHONE': settings.CONTACT_PHONE,
            'CONTACT_EMAIL': settings.CONTACT_EMAIL,
            'SHOW_INCIDENTS': settings.SHOW_INCIDENTS,
            'SHOW_UPTIME': settings.SHOW_UPTIME,
            'SHOW_LAST_INCIDENT': settings.SHOW_LAST_INCIDENT,
            'twitter_account': twitter_account()}