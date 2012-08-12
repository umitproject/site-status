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

from main.feeds import LastModuleStatuses

handler500 = 'djangotoolbox.errorviews.server_error'

urlpatterns = patterns('',
    url('^/?$', 'main.views.home', name='home'),
    url('^event/(?P<event_id>\d+)/?$', 'main.views.event', name='event'),

    ####################
    #  subscribe-related urls
    url('^subscribe/event/(?P<event_id>\d+)/?$', 'main.views.subscribe', name='event_subscribe'),
    url('^subscribe/module/(?P<module_id>\d+)/?$', 'main.views.subscribe', name='module_subscribe'),
    url('^subscribe/?$', 'main.views.subscribe', name='system_subscribe'),
    url('^subscribe/manage/(?P<uuid>[a-fA-F0-9\-]+)?$', 'main.views.manage_subscriptions', name='manage_subscription'),
    url('^subscribe/settings/?$', 'main.views.subscriber_setting', name='subscriber_settings'),
    url('^unsubscribe/?$', 'main.views.unsubscribe', name='unsubscribe'),
    
    ########
    # FEEDS
    url(r'^feeds/(?P<module_id>\d+)/?$', LastModuleStatuses(), name='feeds'),
    
    ########
    # TESTS
    url('^test_populate/?$', 'main.views.test_populate', name='test_populate'),
    url('^test_events_and_aggregations/?$', 'main.views.test_events_and_aggregations', name='test_events_and_aggregations'),
    url(r'^hard_reset/', 'main.views.hard_reset', name='hard_reset'),

    ######################
    # Notification System
    url(r'^notification/', include('status_notification.urls')),
    
    ########
    # ADMIN
    url(r'^clean_cache/', 'main.views.clean_cache', name='clean_cache'),
)
