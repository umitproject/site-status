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

from django.conf import settings
from django.shortcuts import get_object_or_404
from django.contrib.syndication.views import Feed
from django.contrib.syndication.views import FeedDoesNotExist

from main.models import *

class LastModuleStatuses(Feed):
    
    ###############################################
    # Deals with module related pieces of the feed
    def get_object(self, request, module_id):
        return get_object_or_404(Module, pk=module_id)
    
    def title(self, module):
        return "%s (%s)" % (settings.SITE_NAME, module.name)
    
    def link(self, module):
        # TODO: Provide link according to module been monitored
        return module.url
    
    def description(self, module):
        return module.description
    
    def author_name(self, module):
        return settings.SITE_NAME
    
    def author_link(self, module):
        return settings.MAIN_SITE_URL
    
    def categories(self, module):
        return module.list_tags

    def items(self, module):
        return ModuleEvent.objects.filter(module=module)[:settings.FEED_SIZE]

    ##############################################
    # Deals with event related pieces of the feed
    def item_title(self, event):
        return str(event)

    def item_description(self, event):
        if event.back_at:
            return "%(module)s was down from %(down_at)s to %(back_at)s for a total of %(total_downtime)s minutes. "\
            "Sorry for this inconvenience. We're working hard to prevent such disruptions from happening again." % dict(module=event.module.name,
                                                                                                                        down_at=event.down_at.strftime("%c"),
                                                                                                                        back_at=event.back_at.strftime("%c"),
                                                                                                                        total_downtime=event.total_downtime)
        return "%(module)s is down since %(down_at)s. Sorry for this inconvenience. We're working hard to "\
            "recover our systems and we'll update this feed as soon as we're back!" % dict(module=event.module.name,
                                                                                           down_at=event.down_at.strftime("%c"))
    
    def item_link(self, event):
        return "%s/event/%s" % (settings.SITE_STATUS_URL, event.id)
    
    def item_author_name(self, event):
        return settings.SITE_NAME
    
    def item_author_email(self, event):
        return settings.CONTACT_EMAIL
    
    def item_author_link(self, event):
        return "%s/event/%s" % (settings.SITE_STATUS_URL, event.id)
    
    def item_pubdate(self, event):
        if event.back_at:
            return event.back_at
        return event.down_at
    
    def item_categories(self, event):
        if event.back_at:
            return (event.module.name, event.status, "service reestablished")
        return (event.module.name, event.status, "service is down")