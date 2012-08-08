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

import random
import datetime
import urllib2
import logging
import re
from settings import MONITOR_LOG_PATH
import os

from django.shortcuts import render, render_to_response, get_object_or_404, redirect
from django.http import HttpResponse, Http404
from django.conf import settings
from django.contrib.auth.models import User
from django.template.context import RequestContext
from django.utils import simplejson as json
from django.contrib.auth.decorators import login_required
from django.utils.translation import ugettext_noop as _
import user

from main.decorators import staff_member_required
from main.models import *
from main.forms import *

def root_home(request, msg=None):
    context = RequestContext(request)
    return render(request, 'main/root_home.html', context)

def home(request, msg=None):
    site_config = request.site_config
    modules = Module.objects.filter(site_config=site_config)
    show_days = Module.show_days(site_config)
    last_incident = request.aggregation.last_incident
    current_availability = request.aggregation.percentage_uptime
    scheduled_maintenances = ScheduledMaintenance.objects.\
                                filter(site_config=request.site_config,
                                       scheduled_to__lte=request.site_config.schedule_warning_up_to)
    events = ModuleEvent.objects.filter(site_config=site_config, back_at__lte=(datetime.datetime.now()-datetime.timedelta(days=7)) )

    incidents_data = json.dumps(request.aggregation.incidents_data)
    uptime_data = json.dumps(request.aggregation.uptime_data)
    SHOW_LAST_INCIDENT = True
    SHOW_INCIDENTS = True
    SHOW_UPTIME = True
    
    context = locals()
    if msg is not None:
        context['msg'] = msg
    return render(request, 'main/home.html', context)

def event(request, event_id):
    # TODO: Must show event details
    event = get_object_or_404(ModuleEvent, pk=event_id)
    scheduled_maintenances = ScheduledMaintenance.objects.filter(module=event.module)
    
    context = locals()
    return render(request, 'main/event.html', context)

#############################
# SUBSCRIPTION RELATED VIEWS
def subscribe(request, event_id=None, module_id=None):
    """Possible behaviors:
    
    1 - If no id is provided
      - We show the full form, and let user decide whether he want to remain
        subscribed to receive whatever status for this system or receive a
        one time notification once this system have recovered from current
        disruption.
    2 - If event_id is provided
      - We show the full form, and let user decide whether he want to remain
        subscribed to receive whatever status for this event or receive a
        one time notification once this event have recovered from current
        disruption. If event is recovered, let user subscribe to the module
        instead and don't show one-time option.
    3 - If module_id is provided
      - We show the full form, and let user decide whether he want to remain
        subscribed to receive whatever status for this module or receive a
        one time notification once this module have recovered from current
        disruption. If module is online, let user subscribe to the module
        instead and don't show one-time option.
    """
    system = False
    module = False
    event = False
    one_time = False
    form = None
    saved = False
    
    if (event_id is not None) and (module_id is None):
        event = get_object_or_404(ModuleEvent, pk=event_id)
        one_time = not event.back_at
    elif (event_id is None) and (module_id is not None):
        module = get_object_or_404(Module, pk=module_id)
        one_time = module.status != 'on-line'
    else:
        system = True
        one_time = request.aggregation.status != 'on-line'
    
    if one_time:
        if request.POST:
            form = SubscribeOneTimeForm(request.POST)
        else:
            form = SubscribeOneTimeForm()
    else:
        if request.POST:
            form = SubscribeForm(request.POST)
        else:
            form = SubscribeForm()
    
    if form.is_valid():
        # Now, we need to check if user opted for one_time or not
        one_time = form.cleaned_data.get('one_time', False)
        email = form.cleaned_data['email']
        
        subscriber = Subscriber.objects.filter(email=email)
        if not subscriber:
            subscriber = Subscriber()
            subscriber.created_at = datetime.datetime.now()
            subscriber.last_access = subscriber.created_at
            subscriber.email = email
            subscriber.subscribed = True
        else:
            subscriber = subscriber[0]
            subscriber.last_access = datetime.datetime.now()
        
        subscriber.add_ip(request.META['REMOTE_ADDR'])
        subscriber.site_config = request.site_config
        subscriber.save()
        
        if module:
            saved = subscriber.subscribe('module', one_time, module.id)
        if event:
            saved = subscriber.subscribe('event', one_time, event.id) or saved
        if not module and not event:
            saved = subscriber.subscribe('system', one_time, None) or saved
    
    context = locals()
    return render(request, 'main/subscribe.html', context)

def manage_subscriptions(request,uuid=None):
    if uuid is not None:
        subscriber = get_object_or_404(Subscriber, unique_identifier=uuid)
        subscriber_settings = SubscriberSettings(instance=subscriber)
        subscriptions = subscriber.list_subscriptions
        unsubscribe_formset = UnsubscribeFormFactory(initial=[dict({'uuid':subscriber.unique_identifier, 'subscription_id':s.id}) for s in subscriptions])
        unsubscribe_all_form = UnsubscribeAllForm(initial=dict({'uuid':subscriber.unique_identifier}))


        i=0 #this just feels wrong
        for form in unsubscribe_formset:
            form.instance = subscriptions[i]
            i += 1
        i=None
    else:
        if request.method == 'GET':
            get_link_form = SubscribeForm()
        elif request.method == 'POST':
            get_link_form = SubscribeForm(request.POST)
            if get_link_form.is_valid():
                email = get_link_form.cleaned_data.get("email")
                subscriber = Subscriber.objects.get(email=email,site_config=request.site_config)
                if subscriber:
                    url = "://%s%s"%(request.get_host(),subscriber.management_url)
                    url = "https" + url if request.is_secure() else "http" + url
                    email = EmailMessage(subject="Your subscription management link",
                                         body="Please use this link to manage your subscription for %s:\n%s"%(subscriber.site_config.site_name,url),
                                         to=(subscriber.email,))
                    email.send()
                    sent=True
                    subscriber=None

    context=locals()
    return render(request, 'main/manage_subscription.html', context)

def unsubscribe(request):
    if request.method == 'POST':
        subscriber = None
        submitted_data = request.POST.copy()
        unsubscribe_all = submitted_data.get("unsubscribe_all")
        if unsubscribe_all:
            form = UnsubscribeAllForm(request.POST)
        else:
            form = UnsubscribeFormFactory(submitted_data)
        if form.is_valid():
            if unsubscribe_all:
                uuid = submitted_data.get("uuid")
                subscriber = Subscriber.objects.get(unique_identifier = uuid)
                subscriptions = subscriber.list_subscriptions
                for subscription in subscriptions:
                    subscriber.unsubscribe(subscription.notification_type, subscription.one_time, subscription.target_id)
                subscriber.delete()
                return redirect("/")
            else:
                for data in form.cleaned_data:
                    uuid = data.get("uuid")
                    subscription_id = data.get("subscription_id")

                    subscriber = Subscriber.objects.get(unique_identifier = uuid)
                    subscription = NotifyOnEvent.objects.get(id=subscription_id)
                    subscriber.unsubscribe(subscription.notification_type, subscription.one_time, subscription.target_id)
                    if not len(subscriber.list_subscriptions_ids):
                        subscriber.delete()
                        return redirect("/")
                    else:
                        return redirect(subscriber.management_url)

    return redirect("manage_subscription")

def subscriber_setting(request):
    if request.method == 'POST':
        uuid = request.POST.get("unique_identifier")
        instance = Subscriber.objects.get(unique_identifier=uuid)
        form = SubscriberSettings(request.POST,instance=instance)
        if form.is_valid():
            form.save()
            return redirect(form.instance.management_url)

    return redirect("/")


###############################################################################
# ADMIN VIEWS                                                                 #
###############################################################################
@staff_member_required
def clean_cache(request):
    msg = ''
    if memcache.flush_all():
        msg = _('Flush cache OK')
    else:
        msg = _('Flush cache FAILED')
    return home(request, msg)


###############################################################################
# TEST RELATED VIEWS                                                          #
###############################################################################
def _create_fake_events(module, range_days):
    today = datetime.datetime.now()
    time = today - datetime.timedelta(days=range_days)
    events = []
    for i in xrange(range_days):
        for j in xrange(random.randrange(1, 24, 1)):
            event = ModuleEvent()
            event.status = random.choice(STATUS)[0]
            event.module = module
            event.down_at = time
            event.back_at = time + datetime.timedelta(minutes=random.randrange(1, 60, 2))
            event.save()
            
            events.append(event)
        
        time = time + datetime.timedelta(days=1)

def _create_fake_module(name, description, module_type, host, url):
    range_days = 7
    
    mod = Module()
    mod.name = name
    mod.monitoring_since = datetime.datetime.now() - datetime.timedelta(days=10)
    mod.description = description
    mod.module_type = module_type
    mod.host = host
    mod.url = url
    mod.status = 'on-line'

    site_config = SiteConfig.objects.filter(site_name=name)
    if not site_config:
        site_config = SiteConfig()
        site_config.site_name = name
        site_config.main_site_url = url

    mod.site_config = site_config

    mod.save()
    
    _create_fake_events(mod, range_days)

@staff_member_required
def test_populate(request):
    if settings.DEBUG:
        if not Module.objects.filter(name="Umit Project"):
            _create_fake_module("Umit Project",
                                "This is our main website.",
                                "passive",
                                "www.umitproject.org",
                                "http://www.umitproject.org")
        
        if not Module.objects.filter(name="Trac"):
            _create_fake_module("Trac",
                                "This is our old development site, based on Trac.",
                                "passive",
                                "trac.umitproject.org",
                                "http://trac.umitproject.org")
        
        if not Module.objects.filter(name="Redmine"):
            _create_fake_module("Redmine",
                                "This is our new development site, based on Redmine.",
                                "passive",
                                "dev.umitproject.org",
                                "http://dev.umitproject.org")
        
        if not Module.objects.filter(name="Git"):
            _create_fake_module("Git",
                                "This is our git repository.",
                                "passive",
                                "git.umitproject.org",
                                "http://git.umitproject.org")
        
        if not Module.objects.filter(name="Blog"):
            _create_fake_module("Blog",
                                "This is our blog.",
                                "passive",
                                "blog.umitproject.org",
                                "http://blog.umitproject.org")
        
        # Create test user
        if not User.objects.filter(username='admin'):
            user = User.objects.create_user('admin', 'adriano@umitproject.org', 'test')
            user.is_staff = True
            user.is_superuser = True
            user.is_active = True
            user.save()
        
        # Create Twitter Account
        if not TwitterAccount.objects.filter(login='umit_project'):
            twitter_account = TwitterAccount()
            twitter_account.login = 'umit_project'
            twitter_account.api_key = ''
            twitter_account.api_secret = ''
            twitter_account.post_tweet_automatically = True
            twitter_account.monitor_stream = True
            twitter_account.monitor_stream_terms = ''
            twitter_account.save()
        
        return home(request, 'Test Populate OK')
    
    raise Http404

@staff_member_required
def test_events_and_aggregations(request):
    modules = Module.objects.all()
    for module in modules:
        _create_fake_events(module, 7)
    
    return home(request, 'Test Events and Aggregations OK')

@staff_member_required
def hard_reset(request):
    [m.delete() for m in Module.objects.all()]
    [e.delete() for e in ModuleEvent.objects.all()]
    [d.delete() for d in DailyModuleStatus.objects.all()]
    
    memcache.flush_all()
    
    return home(request, 'Flush cache FAILED')

@login_required
def log(request, log_name):
    try:
        u = request.user
        match = re.match('^monitor(\d+).log(.(\d+-\d+-\d+))?$',log_name)
        if match:
            module_id = int(match.group(1))
            module = Module.objects.get(pk=module_id)
            if module.site_config.user.username == u.username:
                response = HttpResponse(module.logs, mimetype='text/plain')
                response['Cache-Control'] = 'no-cache'
                return response
    except Exception,e:
        raise Http404
    raise Http404

