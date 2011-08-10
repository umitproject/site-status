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

from django.conf.urls.defaults import *

urlpatterns = patterns('',
    url('^report_status/?$', 'status_api.views.report_status', name='report_status'),
    url('^check_status/?$', 'status_api.views.check_status', name='check_status'),
    url('^check_incidents/?$', 'status_api.views.check_incidents', name='check_incidents'),
    url('^check_downtime/?$', 'status_api.views.check_downtime', name='check_downtime'),
    url('^check_uptime/?$', 'status_api.views.check_uptime', name='check_uptime'),
    url('^check_availability/?$', 'status_api.views.check_availability', name='check_availability'),
)