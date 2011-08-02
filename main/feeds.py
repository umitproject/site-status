#!/usr/bin/env python

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
        return event.module.url
    
    def item_author_name(self, event):
        return settings.SITE_NAME
    
    def item_author_email(self, event):
        return settings.CONTACT_EMAIL
    
    def item_author_link(self, event):
        return settings.MAIN_SITE_URL
    
    def item_pubdate(self, event):
        if event.back_at:
            return event.back_at
        return event.down_at
    
    def item_categories(self, event):
        if event.back_at:
            return (event.module.name, event.status, "service reestablished")
        return (event.module.name, event.status, "service is down")