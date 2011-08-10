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
    url('^check_passive_hosts/?$', 'status_cron.views.check_passive_hosts', name='check_passive_hosts'),
    url('^check_passive_hosts_task/(?P<module_key>[0-9a-zA-Z\-\_]+)/?$', 'status_cron.views.check_passive_hosts_task', name='check_passive_hosts_task'),
    url('^aggregate_daily_status/?$', 'status_cron.views.aggregate_daily_status', name='aggregate_daily_status'),
    url('^check_notifications/?$', 'status_cron.views.check_notifications', name='check_notifications'),
    url('^send_notification_task/(?P<notification_id>[0-9a-zA-Z\-\_]+)/?$', 'status_cron.views.send_notification_task', name='send_notification_task'),
)