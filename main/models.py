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

import datetime
import logging
import re
import uuid
import itertools

from decimal import *
from types import StringTypes
from django.core import validators
from django.contrib.auth.models import User
from django.core.validators import RegexValidator

from django.db import models
from django.db.models import Q
from django.db.models.signals import post_save, pre_save
from django.template.loader import render_to_string
from django.conf import settings
from django.utils.translation import ugettext_lazy as _
from django.core.cache import cache

from main.memcache import memcache
from settings import SUBSCRIBER_EDIT_EXPIRATION,DOMAIN_SITE_CONFIG_CACHE_KEY, SITE_CONFIG_CACHE_KEY
from main.utils import pretty_date

from dbextra.fields import ListField

##########
# CHOICES
from settings import DEFAULT_NOTIFICATION_DEBOUNCE_TIMER
from django.core.urlresolvers import reverse, NoReverseMatch

STATUS = (
          ('on-line', _('On-line')),
          ('off-line', _('Off-line')),
          ('smaintenance', _('Scheduled Maintenance')),
          ('maintenance', _('Maintenance')),
          ('read-only', _('Read-Only')),
          ('investigating', _('Investigating')),
          ('updating', _('Updating')),
          ('service_disruption', _('Service Disruption')),
          ('unknown', _('Unknown')),
          )

MODULE_TYPES = (
                ('url_check', _('URL Check')),
                ('port_check', _('Port Check')),
                ('active', _('Active')),
                )

NOTIFICATION_TYPES = (
                      ('module', _('Module')),
                      ('event', _('Event')),
                      ('system', _('System')),
                      ('scheduling', _('Scheduling')),
                      )

PORT_CHECK_OPTIONS = (
    (80, _('HTTP: 80')),
    (443, _('HTTPS: 443')),
    (22, _('SSH/SFTP: 22')),
    (21, _('FTP: 20')),
    (25, _('SMTP: 25')),
    (3306, _('MYSQL: 3306')),
    (110, _('POP3: 110')),
    (143, _('IMAP: 143'))
)

MONITOR_LOG_SEPARATOR = ' '

################
# MEMCACHE KEYS
MODULE_TODAY_STATUS_KEY = 'module_today_status_%s'
MODULE_DAY_STATUS_KEY = 'module_day_status_%s_%s__%s'
SITE_CONFIG_KEY = 'site_config_%s'
MODULE_EVENT_CURRENT = 'current_events_for_module_%s'


###################
# Helper Functions

def status_img(status):
    return 'img/%s.gif' % status

def verbose_status(status):
    return dict(STATUS)[status]

def timedelta_seconds(delta):
    return (delta.days * 24 * 60 * 60) + delta.seconds + (delta.microseconds/1000000)

def percentage(value, total):
    if type(value) not in StringTypes:
        value = '%.2f' % value
    if type(total) not in StringTypes:
        total = '%.2f' % total
    
    total = Decimal(total)
    if total:
        perc = round((Decimal(value) * Decimal(100)) / Decimal(total), 2)
        if perc > Decimal(100):
            return 100
        return perc

    return 100

class StatusSiteDomain(models.Model):
    status_url = models.CharField(max_length=255, unique=True)
    site_config = models.ForeignKey('main.SiteConfig')
    public = models.BooleanField(default=False)
    
    def __unicode__(self):
        return '%s -> %s' % (self.status_url, self.site_config.site_name)

    def save(self, *args, **kwargs):
        super(StatusSiteDomain, self).save(*args, **kwargs)
        memcache.delete(DOMAIN_SITE_CONFIG_CACHE_KEY % self.status_url)

class SiteConfig(models.Model):
    created_at = models.DateTimeField(auto_now_add=True)
    site_name = models.CharField(max_length=200, help_text="Public name for the site.")
    main_site_url = models.CharField(max_length=500, null=True, blank=True, default="",
                                    help_text="URL to your main website.")
    contact_phone = models.CharField(max_length=50, null=True, blank=True, default="")
    contact_email = models.EmailField(null=True, blank=True, default="",
                                    help_text="Customer support email.")
    admin_email = models.EmailField(null=True, blank=True, default="")
    feed_size = models.IntegerField(default=5)
    analytics_id = models.CharField(max_length=20, null=True, blank=True, default="")
    twitter_account = models.ForeignKey('main.TwitterAccount', null=True, blank=True, default=None)
    notification_sender = models.EmailField(null=True, blank=True, default=settings.DEFAULT_NOTIFICATION_SENDER)
    notification_to = models.EmailField(null=True, blank=True, default=settings.DEFAULT_NOTIFICATION_TO)
    notification_reply_to = models.EmailField(null=True, blank=True, default=settings.DEFAULT_NOTIFICATION_REPLY_TO)
    show_days = models.IntegerField(default=7)
    schedule_warning_time = models.IntegerField(default=7, help_text="in minutes")
    show_incidents = models.BooleanField(default=settings.DEFAULT_SHOW_INCIDENTS)
    show_uptime = models.BooleanField(default=settings.DEFAULT_SHOW_UPTIME)
    show_last_incident = models.BooleanField(default=settings.DEFAULT_SHOW_LAST_INCIDENT)
    user_theme_selection = models.BooleanField(default=True)
    send_notifications_automatically = models.BooleanField(default=True)
    api_key = models.CharField(max_length=100, null=True, blank=True)
    api_secret = models.CharField(max_length=100, null=True, blank=True)
    public_internal_url = models.BooleanField(default=False)
    logo = models.TextField(null=True,blank=True)
    custom_css = models.TextField(null=True, blank=True)
    slug= models.CharField(max_length=30, null=False, unique=True,\
                            validators=[validators.validate_slug],\
                            help_text="Unique name to identify your site status.")

    preview_logo = models.TextField(null=True,blank=True)
    preview_custom_css = models.TextField(null=True, blank=True)
    user = models.ForeignKey(User)
    
    @staticmethod
    def get_from_domain(domain):
        """
        gets a site_config from its associated domain. It first tries to pull from memcached
        """
        site_config, public = cache.get(DOMAIN_SITE_CONFIG_CACHE_KEY % domain, (False, True))
        if site_config:
            return site_config, public
        status_site = StatusSiteDomain.objects.filter(status_url=domain)
        if status_site:
            cache.set(DOMAIN_SITE_CONFIG_CACHE_KEY % domain, (status_site[0].site_config, status_site[0].public))
            return status_site[0].site_config, status_site[0].public
        return None, True


    @staticmethod
    def get_from_id(id):
        """
        wrapper that tries to get the site_config from memcached first
        """
        site_config = cache.get(SITE_CONFIG_CACHE_KEY % id, False)
        if site_config:
            return site_config
        site_config = SiteConfig.objects.get(id=id)
        if site_config:
            cache.set(SITE_CONFIG_CACHE_KEY % site_config.id, site_config)
        return site_config

    
    @property
    def schedule_warning_up_to(self):
        return datetime.datetime.now() + datetime.timedelta(minutes=self.schedule_warning_time)

    @property
    def is_public(self):
        return StatusSiteDomain.objects.filter(site_config=self).exists()

    @property
    def list_urls(self):
        return [(reverse("home", args=[self.slug]) , self.public_internal_url),] + [("http://" + s.status_url, s.public) for s in StatusSiteDomain.objects.filter(site_config=self)]

    @property
    def aggregated_status(self):
        return AggregatedStatus.objects.get(site_config=self)


    def save(self, *args, **kwargs):
        memcache.delete(SITE_CONFIG_KEY % self.site_name)
        memcache.delete(SITE_CONFIG_CACHE_KEY % self.id)
        
        if not self.api_key:
            self.api_key = uuid.uuid4()
        
        if not self.api_secret:
            self.api_secret = uuid.uuid4()
        
        super(SiteConfig, self).save(*args, **kwargs)
    
    def __unicode__(self):
        return self.site_name

class Subscriber(models.Model):
    '''Full list of all users who ever registered asking to be notified.
    Used for consultation on when was last time user accessed the status site
    or since when he is registered, as well as his email that is used as a key.
    '''
    unique_identifier = models.CharField(max_length=36, blank=True, null=True, default='')
    created_at = models.DateTimeField(null=True, blank=True, default=None)
    updated_at = models.DateTimeField(null=True, blank=True, default=None)
    email = models.EmailField()
    subscriptions = models.TextField()
    originating_ips = models.TextField()
    unsubscribed_at = models.DateTimeField(null=True, blank=True, default=None)
    site_config = models.ForeignKey('main.SiteConfig', null=True)
    debounce_timer = models.IntegerField(null=True, blank=True, default=None)
    edit_token = models.CharField(max_length=36, blank=True, null=True, default='')
    edit_token_expiration = models.DateTimeField(null=True, blank=True, default=None)


    @property
    def list_subscriptions_ids(self):
        if not self.subscriptions:
            return []
        return [int(s) for s in self.subscriptions.split(',') if s != '']
    
    @property
    def list_subscriptions(self):
        if not self.subscriptions:
            return []
        return [NotifyOnEvent.objects.get(pk=int(s)) for s in self.subscriptions.split(',')]
    
    @property
    def list_ips(self):
        if not self.originating_ips:
            return []
        return self.originating_ips.split(',')


    # always call this before editing the subscription
    @property
    def can_be_edited(self):
        if self.edit_token and self.edit_token_expiration and datetime.datetime.now() < self.edit_token_expiration:
            return True
        if self.edit_token:
            self.edit_token = None
            self.save()
        return False

    def request_edit_token(self):
        self.edit_token_expiration = datetime.datetime.now() + datetime.timedelta(seconds=SUBSCRIBER_EDIT_EXPIRATION)
        self.edit_token = str(uuid.uuid4())
        self.save()


    @property
    def management_url(self):
        try:
            return reverse('manage_subscription', kwargs={'uuid':self.edit_token})
        except NoReverseMatch:
            return reverse('manage_subscription', kwargs={'site_slug' : self.site_config.slug, 'uuid':self.edit_token})
    
    def add_ip(self, ip):
        list_ips = self.list_ips
        if ip not in list_ips:
            list_ips.append(ip)
            self.originating_ips = ','.join(list_ips)
            return True
        return False
    
    def add_subscription(self, notification_id):
        subs_ids = self.list_subscriptions_ids
        if notification_id not in subs_ids:
            subs_ids.append(notification_id)
            self.subscriptions = ','.join([str(id) for id in subs_ids])
            return True
        return False
    
    def remove_subscription(self, notification_id):
        subs_ids = self.list_subscriptions_ids
        if notification_id in subs_ids:
            subs_ids.remove(notification_id)
            self.subscriptions = ','.join([str(id) for id in subs_ids])
            return True
        return False
    
    def save(self, *args, **kwargs):
        # This is in order to have a unique ID that is safe to be exposed.
        # The entity id is a sequential number that is too easy to guess.
        # Beware we must do this only once. Otherwise, the id would change
        # after a save.
        if not self.unique_identifier:
            self.unique_identifier = str(uuid.uuid4())
        
        super(Subscriber, self).save(*args, **kwargs)
    
    def unsubscribe(self, notification_type, one_time, target_id=None):
        return NotifyOnEvent.unsubscribe(self.email,
                                         notification_type,
                                         one_time,
                                         target_id,
                                         site_config=self.site_config)
    
    def subscribe(self, notification_type, one_time, target_id=None):
        notification = NotifyOnEvent.objects.filter(notification_type=notification_type,
                                                    one_time=one_time, target_id=target_id,
                                                    site_config=self.site_config)
        
        if not notification:
            notification = NotifyOnEvent(created_at=datetime.datetime.now(),
                                         notification_type=notification_type,
                                         one_time=one_time, target_id=target_id,
                                         site_config=self.site_config)
        else:
            notification = notification[0] 
        
        notification.add_email(self.email)
        notification.save()

        self.add_subscription(notification.id)
        self.save()
        
        return notification
    
    def __unicode__(self):
        return self.email

class Notification(models.Model):
    """When an event happens, a notification is created.
    When a notification is created, the pre_save signal must go look for
    the relevant NotifyOnEvent instances and save the emails it will need
    to send out.
    """
    created_at = models.DateTimeField(null=True, blank=True, default=None)
    sent_at = models.DateTimeField(null=True, blank=True, default=None)
    send = models.BooleanField(default=True)
    notification_type = models.CharField(max_length=10, choices=NOTIFICATION_TYPES)
    target_id = models.IntegerField(null=True, blank=True, default=None)
    subject = models.CharField(max_length=400)
    body = models.TextField()
    html = models.TextField()
    emails = models.TextField()
    previous_status = models.CharField(max_length=20)
    current_status = models.CharField(max_length=20)
    downtime = models.DecimalField(max_digits=5, decimal_places=2,
                                   default=None, null=True)
    site_config = models.ForeignKey('main.SiteConfig', null=True)

    def __unicode__(self):
        return "%s - %s -%s" % ("Send" if self.send else "Not send", self.subject, self.current_status)
    
    @property
    def list_emails(self):
        if not self.emails:
            return []
        return [e for e in self.emails.split(',') if e]
    
    def build_email_data(self):
        target_url = self.site_config.main_site_url
        target_name = self.site_config.site_name
        
        if self.notification_type == 'event':
            event = ModuleEvent.objects.get(pk=self.target_id)
            target_url = event.module.url
            target_name = event.module.name
        elif self.notification_type == 'module':
            module = Module.objects.get(pk=self.target_id)
            target_url = module.url
            target_name = module.name
        
        context = dict(TARGET_URL=target_url,
                       TARGET_NAME=target_name)
        
        self.subject = "%s is back!" % target_name
        logging.info("Building email data for %s. Subject: %s" % (target_name, self.subject))
        
        self.body = render_to_string('status_notification/notification_body.txt', context)
        self.html = render_to_string('status_notification/notification_body.html', context)
        self.save()
    
    def save(self, *args, **kwargs):
        if not self.id:
            self._retrieve_emails()
        
        super(Notification, self).save(*args, **kwargs)
    
    def _notify_emails(self, notification_type, one_time, target_id):
        notify = None
        now = datetime.datetime.now()
        if one_time:
            notify = NotifyOnEvent.objects.filter(one_time=one_time,
                                                  notification_type=notification_type,
                                                  target_id=target_id,
                                                  last_notified=None,
                                                  site_config=self.site_config)
        else:
            notify = NotifyOnEvent.objects.filter(one_time=one_time,
                                                  notification_type=notification_type,
                                                  target_id=target_id,
                                                  site_config=self.site_config)
            
        if notify:
            notify = notify[0]
        else:
            notify = []
        
        return notify

    def _retrieve_emails(self):
        notifications = []
        
        # System wide
        notifications.append(self._notify_emails('system', False, None))
        
        # System wide one_time
        notifications.append(self._notify_emails('system', True, None))
        
        # Specific event
        if self.notification_type == 'event':
            # We need to notify event and module also
            notifications.append(self._notify_emails(self.notification_type, True, self.target_id))
            
            module = ModuleEvent.objects.get(pk=self.target_id).module
            
            if module:
                notifications.append(self._notify_emails('module', False, module.id))
                notifications.append(self._notify_emails('module', True, module.id))
        elif self.notification_type == 'module':
            notifications.append(self._notify_emails(self.notification_type, True, self.target_id))
            notifications.append(self._notify_emails(self.notification_type, False, self.target_id))


        emails = []
        for n in notifications:
            if not n:
                continue
            list_emails = n.list_emails
            for email in list_emails:
                if email not in emails:
                    s = Subscriber.objects.get(email=email)
                    # is not a subscriber (added through other ways) or is a subscriber that wasn't notified in a while
                    if not s or (s and (not n.last_notified or n.last_notified < datetime.datetime.now() - datetime.timedelta(seconds=s.debounce_timer or DEFAULT_NOTIFICATION_DEBOUNCE_TIMER))):
                        emails.append(email)


        self.emails = ','.join(emails)

        now = datetime.datetime.now()
        for notification in notifications:
            if notification != []:
                notification.last_notified = now
                notification.save()


class NotifyOnEvent(models.Model):
    '''Aggregation for all users who asked to be notified about an specific
    event only once (site is offline now, and she wants to be informed when
    it is back) or always (whenever there is a status change for a module or
    system).
    '''
    created_at = models.DateTimeField(null=True, blank=True, default=None)
    last_notified = models.DateTimeField(null=True, blank=True, default=None)
    one_time = models.BooleanField(default=False)
    notification_type = models.CharField(max_length=10, choices=NOTIFICATION_TYPES)
    target_id = models.IntegerField(null=True, blank=True, default=None)
    emails = models.TextField()
    site_config = models.ForeignKey('main.SiteConfig', null=True)
    
    @property
    def list_emails(self):
        if not self.emails:
            return []
        return self.emails.split(',')
    
    def add_email(self, email):
        list_emails = self.list_emails
        if email not in list_emails:
            list_emails.append(email)
            self.emails = ','.join(list_emails)
            return True
        return False
    
    def remove_email(self, email):
        list_emails = self.list_emails
        if email in list_emails:
            list_emails.remove(email)
            self.emails = ','.join(list_emails)
            return True
        return False

    @property
    def target_name(self):
        if self.notification_type == "system":
            return "ALL"
        if self.notification_type == "module":
            module = Module.objects.get(id=self.target_id)
            if module:
                return module.name
        if self.notification_type == "event":
            module_event = ModuleEvent.objects.get(id=self.target_id)
            if module_event:
                return module_event.module.name
        return ""

    @staticmethod
    def can_unsubscribe(email, notification_type, one_time, target_id=None):
        instance = NotifyOnEvent.objects.get(notification_type=notification_type,
                                                one_time=one_time,
                                                target_id=target_id,
                                                site_config=self.site_config)
        if instance and email in instance.list_emails:
            return True
        return False
    
    @staticmethod
    def unsubscribe(email, notification_type, one_time, target_id=None, site_config=None):
        instance = NotifyOnEvent.objects.get(notification_type=notification_type,
                                                one_time=one_time,
                                                target_id=target_id,
                                                site_config=site_config)


        list_emails = instance.list_emails
        if instance and email in list_emails:
            # Removing the NotifyOnEvent id from subscriber's instance
            subscriber = Subscriber.objects.get(email=email, site_config=site_config)

            subs_ids = subscriber.list_subscriptions_ids
            subs_ids.remove(instance.id)
            subscriber.subscriptions = ','.join([str(id) for id in subs_ids])
            subscriber.save()
            
            # Removing subscriber's email from NotifyOnEvent instance
            if len(list_emails) == 1:
                instance.delete()
            else:
                list_emails.remove(email)
                instance.emails = ','.join([str(e) for e in list_emails])
                instance.save()
            
            return True
        return False
    
    def __unicode__(self):
        return '%s (%s) - %s' % (self.notification_type, self.target_id,
                          'notified' if self.last_notified else 'not notified')


class AggregatedStatus(models.Model):
    created_at = models.DateTimeField(null=True, blank=True, default=None)
    updated_at = models.DateTimeField(null=True, blank=True, default=None)
    time_estimate_all_modules = models.FloatField(default=0.0)
    status = models.CharField(max_length=30, choices=STATUS, default=STATUS[0][0])
    site_config = models.ForeignKey('main.SiteConfig', null=True)

    @property
    def total_time(self):
        """
        Sum of monitors total_time
        """
        modules = Module.objects.filter(site_config=self.site_config)
        total_time = 0
        for module in modules:
            total_time += module.total_time
        return total_time

    @property
    def total_public_time(self):
        """
        Sum of public monitors total_time
        """
        modules = Module.objects.filter(site_config=self.site_config, public=True)
        total_time = 0
        for module in modules:
            total_time += module.total_time
        return total_time

    @property
    def total_downtime(self):
        """
        Sum of monitors down_time
        """
        modules = Module.objects.filter(site_config=self.site_config)
        total_downtime = 0
        for module in modules:
            total_downtime += module.total_downtime
        return total_downtime

    @property
    def total_public_downtime(self):
        """
        Sum of monitors down_time
        """
        modules = Module.objects.filter(site_config=self.site_config, public=True)
        total_downtime = 0
        for module in modules:
            total_downtime += module.total_downtime
        return total_downtime


    @property
    def total_uptime(self):
        return self.total_time - self.total_downtime


    @property
    def total_public_uptime(self):
        return self.total_public_time - self.total_public_downtime

    @property
    def percentage_downtime(self):
        return percentage(self.total_downtime, self.total_time) if self.total_time > 0 else 0


    @property
    def public_percentage_downtime(self):
        return percentage(self.total_public_downtime, self.total_public_time) if self.total_public_time > 0 else 0

    @property
    def percentage_uptime(self):
        return 100 - self.percentage_downtime


    @property
    def public_percentage_uptime(self):
        return 100 - self.public_percentage_downtime

    @property
    def incidents_data(self):
        now = datetime.datetime.now()
        today = datetime.datetime(now.year, now.month, now.day, 0, 0, 0)
        total_base = Module.objects.filter(site_config=self.site_config).count() * 24 * 60 # Total minutes all modules can be offline in a day

        no_days = self.site_config.show_days
        first_day = today - datetime.timedelta(days=no_days)
        impacting_events = ModuleEvent.objects.filter(Q(back_at__isnull=True) | Q(back_at__gte=first_day), site_config=self.site_config)
        
        incidents = []
        for i in xrange(no_days-1, -1, -1):
            day = today - datetime.timedelta(days=i)
            day_end = datetime.datetime(day.year, day.month, day.day, 23, 59, 59, 999999)
            if day_end > now:
                day_end = now

            key = '%s/%s' % (day.month, day.day)
            incident = [key, 0]

            for event in impacting_events:
                impacting_downtime = 0
                if day < event.down_at < day_end:
                    if (event.back_at or day_end) < day_end:
                        impacting_downtime = event.total_downtime
                    else:
                        impacting_downtime = (day_end - event.down_at).total_seconds() / 60
                elif event.down_at < day <= (event.back_at or day_end):
                    if (event.back_at or day_end) < day_end:
                        impacting_downtime = (event.back_at - day).total_seconds() / 60
                    else:
                        impacting_downtime = (day_end - day).total_seconds() / 60


                incident[1] += impacting_downtime

            else:
                incident[1] = percentage(incident[1], total_base)

            incidents.append(incident)

        return incidents

    @property
    def public_incidents_data(self):
        now = datetime.datetime.now()
        today = datetime.datetime(now.year, now.month, now.day, 0, 0, 0)
        total_base = Module.objects.filter(site_config=self.site_config, public=True).count() * 24 * 60 # Total minutes all modules can be offline in a day

        no_days = self.site_config.show_days
        first_day = today - datetime.timedelta(days=no_days)
        impacting_events = ModuleEvent.objects.filter(Q(back_at__isnull=True) | Q(back_at__gte=first_day), site_config=self.site_config, module__public=True)

        incidents = []
        for i in xrange(no_days-1, -1, -1):
            day = today - datetime.timedelta(days=i)
            day_end = datetime.datetime(day.year, day.month, day.day, 23, 59, 59, 999999)
            if day_end > now:
                day_end = now

            key = '%s/%s' % (day.month, day.day)
            incident = [key, 0]

            for event in impacting_events:
                impacting_downtime = 0
                if day < event.down_at < day_end:
                    if (event.back_at or day_end) < day_end:
                        impacting_downtime = event.total_downtime
                    else:
                        impacting_downtime = (day_end - event.down_at).total_seconds() / 60
                elif event.down_at < day <= (event.back_at or day_end):
                    if (event.back_at or day_end) < day_end:
                        impacting_downtime = (event.back_at - day).total_seconds() / 60
                    else:
                        impacting_downtime = (day_end - day).total_seconds() / 60


                incident[1] += impacting_downtime

            else:
                incident[1] = percentage(incident[1], total_base)

            incidents.append(incident)

        return incidents


    @property
    def uptime_data(self):
        now = datetime.datetime.now()
        today = datetime.datetime(now.year, now.month, now.day, 0, 0, 0)
        total_base = Module.objects.filter(site_config=self.site_config).count() * 24 * 60 # Total minutes all modules can be offline in a day

        no_days = self.site_config.show_days
        first_day = today - datetime.timedelta(days=no_days)
        impacting_events = ModuleEvent.objects.filter(Q(back_at__isnull=True) | Q(back_at__gte=first_day), site_config=self.site_config)

        incidents = []
        for i in xrange(no_days-1, -1, -1):
            day = today - datetime.timedelta(days=i)
            day_end = datetime.datetime(day.year, day.month, day.day, 23, 59, 59, 999999)
            if day_end > now:
                day_end = now

            key = '%s/%s' % (day.month, day.day)
            incident = [key, total_base]

            for event in impacting_events:
                impacting_downtime = 0
                if day < event.down_at < day_end:
                    if (event.back_at or day_end) < day_end:
                        impacting_downtime = event.total_downtime
                    else:
                        impacting_downtime = (day_end - event.down_at).total_seconds() / 60
                elif event.down_at < day <= (event.back_at or day_end):
                    if (event.back_at or day_end) < day_end:
                        impacting_downtime = (event.back_at - day).total_seconds() / 60
                    else:
                        impacting_downtime = (day_end - day).total_seconds() / 60


                incident[1] -= impacting_downtime

            else:
                incident[1] = percentage(incident[1], total_base)

            incidents.append(incident)

        return incidents

    @property
    def public_uptime_data(self):
        now = datetime.datetime.now()
        today = datetime.datetime(now.year, now.month, now.day, 0, 0, 0)
        total_base = Module.objects.filter(site_config=self.site_config, public=True).count() * 24 * 60 # Total minutes all modules can be offline in a day

        no_days = self.site_config.show_days
        first_day = today - datetime.timedelta(days=no_days)
        impacting_events = ModuleEvent.objects.filter(Q(back_at__isnull=True) | Q(back_at__gte=first_day), site_config=self.site_config, module__public=True)

        incidents = []
        for i in xrange(no_days-1, -1, -1):
            day = today - datetime.timedelta(days=i)
            day_end = datetime.datetime(day.year, day.month, day.day, 23, 59, 59, 999999)
            if day_end > now:
                day_end = now

            key = '%s/%s' % (day.month, day.day)
            incident = [key, total_base]

            for event in impacting_events:
                impacting_downtime = 0
                if day < event.down_at < day_end:
                    if (event.back_at or day_end) < day_end:
                        impacting_downtime = event.total_downtime
                    else:
                        impacting_downtime = (day_end - event.down_at).total_seconds() / 60
                elif event.down_at < day <= (event.back_at or day_end):
                    if (event.back_at or day_end) < day_end:
                        impacting_downtime = (event.back_at - day).total_seconds() / 60
                    else:
                        impacting_downtime = (day_end - day).total_seconds() / 60


                incident[1] -= impacting_downtime

            else:
                incident[1] = percentage(incident[1], total_base)

            incidents.append(incident)

        return incidents


    @property
    def last_incident(self):
        last_incident = ModuleEvent.objects.exclude(status="").filter(site_config=self.site_config).order_by('-down_at')[:1]
        if last_incident:
            last_incident = last_incident[0]
        
        return last_incident


    @property
    def last_public_incident(self):
        last_incident = ModuleEvent.objects.exclude(status="").filter(site_config=self.site_config, module__public = True).order_by('-down_at')[:1]
        if last_incident:
            last_incident = last_incident[0]

        return last_incident
    
    def __unicode__(self):
        return _('Uptime: %s - Downtime: %s - Availability: %s%% - Status %s') % \
                        (self.total_uptime, self.total_downtime,
                         self.percentage_uptime, self.status)


class DailyModuleStatus(models.Model):
    created_at = models.DateTimeField(null=True, blank=True, default=None)
    updated_at = models.DateTimeField(null=True, blank=True, default=None)
    total_downtime = models.FloatField(default=0.0) # minutes
    statuses = models.TextField()
    events = models.TextField()
    status = models.CharField(max_length=30, choices=STATUS)
    module = models.ForeignKey('main.Module')
    site_config = models.ForeignKey('main.SiteConfig', null=True)

    # TODO: on creation, revoke module's today_status memcache

    @property
    def total_uptime(self):
        return (24*60) - self.total_downtime
    
    @property
    def percentage_uptime(self):
        return percentage(self.total_uptime, 24*60)
    
    @property
    def percentage_downtime(self):
        return percentage(self.total_downtime, self.total_uptime)
    
    def add_status(self, status):
        if status is None or status == "":
            status ='unknown'
        
        self.status = status
        statuses = self.statuses.split(',')
        statuses.append(status)
        self.statuses = ','.join(statuses)
        
        return self.statuses
    
    def add_event(self, event):
        event = str(event)
        if event is None:
            return
        
        events = self.events.strip()
        events = events.split(',')
        if '' in events:
            events.remove('')
        
        if event not in events:
            events.append(event)
        self.events = ','.join(events)
        
        return self.events
    
    @property
    def unique_statuses(self):
        statuses = []
        [statuses.append(s) for s in self.statuses.split(',') if s not in statuses]
        return statuses
        
    @property
    def list_statuses(self):
        return [[s, status_img(s)] for s in self.unique_statuses]
    
    def save(self, *args, **kwargs):
        super(DailyModuleStatus, self).save(*args, **kwargs)
        
        # Revoke cached instances
        memcache.delete(MODULE_DAY_STATUS_KEY % (self.created_at.month, self.created_at.day, self.module.id))
    
    def __unicode__(self):
        return _('%s (%s) had a total downtime %.2d on %s') % (self.module.name,
                                                               self.status,
                                                               self.total_downtime,
                                                               self.created_at)

class ModuleEvent(models.Model):
    down_at = models.DateTimeField(null=True, blank=True, default=None)
    back_at = models.DateTimeField(null=True, blank=True, default=None, db_index=True)
    details = models.TextField()
    status = models.CharField(max_length=30, choices=STATUS)
    module = models.ForeignKey('main.Module', db_index=True)
    site_config = models.ForeignKey('main.SiteConfig', null=True)

    @classmethod
    def current_events_for_module(cls, module):
        cached = cache.get(MODULE_EVENT_CURRENT % module.id, False)
        if cached:
            logging.warning("Returning module events from cache")
            return cached

        queryset = cls.objects.filter(module=module, back_at=None)
        cache.set(MODULE_EVENT_CURRENT % module.id, queryset)

        return queryset
    
    def save(self, *args, **kwargs):
        if self.module.id:
            cache.delete(MODULE_EVENT_CURRENT % self.module.id)

        if self.site_config is None and self.module is not None:
            self.site_config = self.module.site_config
        
        super(ModuleEvent, self).save(*args, **kwargs)
    
    @property
    def total_downtime(self):
        '''Returns total downtime in minutes
        '''
        if self.back_at:
            return float(timedelta_seconds(self.back_at - self.down_at) / 60.0)
        else:
            return float(timedelta_seconds(datetime.datetime.now() - self.down_at) / 60.0)
    
    @property
    def status_img(self):
        return status_img(self.status)
    
    @property
    def verbose_html(self):
        context = dict(status=self.status,
                       event=self,
                       module=self.module,
                       verbose_status=verbose_status(self.status),
                       verbose_time=pretty_date(self.down_at))
        return render_to_string('main/parts/last_incident.html', context) 
    
    @property
    def verbose(self):
        return "%(module)s (%(verbose_status)s) - %(verbose_time)s" % \
                    dict(module=self.module.name,
                         verbose_status=verbose_status(self.status),
                         verbose_time=pretty_date(self.down_at))
    
    def __unicode__(self):
        if self.back_at:
            return _('%s (%s) for %.2d minutes') % (self.module.name,
                                                 self.status,
                                                 self.total_downtime)
        else:
            return _('%s (%s) since %s:%s') % (self.module.name,
                                               self.status,
                                               self.down_at.hour,
                                               self.down_at.minute)

######################
# ModuleEvent signals
def module_event_post_save(sender, instance, created, **kwargs):
    day_status = instance.module.get_day_status(instance.down_at)
    day_status.add_event(instance.id)

    aggregated_statuses = AggregatedStatus.objects.filter(site_config=instance.site_config)
    aggregation = aggregated_statuses[0] if len(aggregated_statuses) > 0 else AggregatedStatus()

    if created:
        instance.module.status = instance.status
        day_status.add_status(instance.status)
        
        aggregation.status = instance.status
    
    if instance.back_at:
        instance.module.status = 'on-line'
        day_status.add_status(instance.module.status)

        day_status.total_downtime += instance.total_downtime

        # Sync aggregation status
        open_event = ModuleEvent.objects.filter(back_at=None, site_config=instance.site_config).order_by('-down_at')[:1]
        if not open_event:
            aggregation.status = 'on-line'
        else:
            aggregation.status = open_event[0].status
        
        # Create notification
        notification = Notification()
        notification.created_at = datetime.datetime.now()
        notification.send = instance.site_config.send_notifications_automatically
        notification.notification_type = 'event'
        notification.target_id = instance.id
        notification.previous_status = instance.status
        notification.current_status = 'on-line'
        notification.downtime = Decimal('%.2f' % instance.total_downtime)
        notification.site_config = instance.site_config
        notification.save()
    
    aggregation.save()
    day_status.save()
    instance.module.save()

post_save.connect(module_event_post_save, sender=ModuleEvent)

class Module(models.Model):
    monitoring_since = models.DateTimeField(null=True, blank=True, default=None)
    updated_at = models.DateTimeField(null=True, blank=True, default=None)
    name = models.CharField(max_length=50, default='')
    description = models.TextField(default=' ', null=True, blank=True)
    module_type = models.CharField(max_length=15, choices=MODULE_TYPES, default=MODULE_TYPES[0]) # two initial types: passive and active. In passive, status site pings the url/port to see if it returns 200. In the active mode, the server sends message to status site to inform its status
    host = models.CharField(max_length=500, help_text="Host name only (no http:// or path).")
    url = models.CharField(max_length=1000,
                            validators=[validators.URLValidator()],
                            error_messages={'url': _('Invalid URL')},
                            help_text='Full URL, including http:// and path.')
    status = models.CharField(max_length=30, choices=STATUS, default=STATUS[3]) # current_status
    tags = models.TextField(default=' ', blank=True, null=True)
    public = models.BooleanField(default=False, help_text=_('Choose whether to show on the status page or not'))
    site_config = models.ForeignKey('main.SiteConfig', null=True)
    logs = ListField()
    
    username = models.CharField(max_length=40, default='', help_text="If url provided requires authentication at HTTP level, you must provide the username", blank=True)
    password = models.CharField(max_length=40, default='', help_text="If url provided requires authentication at HTTP level, you must provide the password", blank=True)

    #url checker
    expected_status = models.IntegerField(default=200, null=True, blank=True,
                                            help_text="HTTP response status code.")
    search_keyword = models.CharField(max_length=30, null=True, blank=True, default=None,
                                            help_text="Keyword or regex to search for in the result page.")

    fail_on_error = models.BooleanField(default=True,
                                        help_text="Returns with failure if the status code is greater than 300.")
    follow_location = models.BooleanField(default=True,
                                        help_text="Follow redirects.")

    #port checker
    check_port = models.IntegerField(null=True, blank=True, default=None, choices=PORT_CHECK_OPTIONS)


    @classmethod
    def get_site_config_modules(cls, site_config):
        modules = cls.objects.filter(site_config=site_config)

        # For active monitors, check if latest check is current. If past 2 min
        # since last update, create event and mark its status as unknown.
        # TODO: Check if unknown is the best status in this situation.
        for module in modules:
            if module.module_type == 'active' and \
               module.updated_at < (datetime.datetime.now() - datetime.timedelta(seconds=120)):
               # This means that the active monitor stopped sending
               # updates. We need to change the module status.
               cls.report_event(module, 'unknown')

        return modules


    @classmethod
    def report_event(cls, module, status):
        new = False
    
        module.updated_at = datetime.datetime.now()
        module.save()

        start = datetime.datetime.now()
        event = ModuleEvent.current_events_for_module(module)

        if not event and status != 'on-line':
            ev = ModuleEvent()
            ev.module = module
            new = True
            event = [ev,]

        for ev in event:
            if status != 'on-line':
                ev.down_at = start
                ev.status = status
            else:
                ev.back_at = start
                ev.down_at = start
                ev.status = status
            ev.save()


    def append_log(self, msg):
        log_tokens = (datetime.datetime.now().isoformat(), )
        if isinstance(msg, tuple):
            log_tokens += msg
        else:
            log_tokens += (msg, )
        self.logs.append(MONITOR_LOG_SEPARATOR.join(log_tokens))
        self.save()

    @property
    def is_url_checker(self):
        return self.module_type == 'url_check'

    @property
    def is_port_checker(self):
        return self.module_type == 'port_check'

    @property
    def list_tags(self):
        if not self.tags:
            return []
        return [tag.strip() for tag in self.tags.split(',')]

    @staticmethod
    def show_days(site_config, days=None):
        modules = Module.objects.filter(site_config=site_config)
        show_days = site_config.show_days

        if days is not None:
            show_days = days

        for module in modules:
            mod_len = len(module.last_7_days)
            if mod_len < show_days:
                show_days = mod_len
        return show_days

    @property
    def status_img(self):
        return 'img/%s.gif' % self.status

    @property
    def total_downtime(self):
        module_events = ModuleEvent.objects.filter(module=self)
        total_downtime = 0.0
        for event in module_events:
            total_downtime += event.total_downtime
        return total_downtime

    @property
    def total_time(self):
        """
         Number of minutes this monitor has run
        """
        return (datetime.datetime.now() - self.monitoring_since).total_seconds() / 60.0

    @property
    def total_uptime(self):
        return self.total_time - self.total_downtime

    @property
    def percentage_uptime(self):
        return 100 - self.percentage_downtime

    @property
    def percentage_downtime(self):
        return percentage(self.total_downtime,self.total_time) if self.total_time else 100

    @property
    def last_7_days(self):
        day = datetime.datetime.now()
        return [self.get_day_status(day - datetime.timedelta(days=d)) for d in xrange(6, -1, -1)]

    @property
    def today_status(self):
        return self.get_day_status(datetime.datetime.now())

    def get_day_status(self, day):
        day_status = memcache.get(MODULE_DAY_STATUS_KEY % (day.month, day.day, self.id), False)

        if day_status:
            return day_status

        day_status = DailyModuleStatus.objects.\
                        filter(module=self).\
                        filter(created_at__gte=datetime.datetime(\
                                 day.year, day.month, day.day, 0, 0, 0)).\
                        filter(created_at__lte=datetime.datetime(\
                                 day.year, day.month, day.day, 23, 59, 59, 999999)).\
                        filter(site_config=self.site_config)

        if day_status:
            memcache.set(MODULE_DAY_STATUS_KEY % (day.month, day.day, self.id), day_status[0])
            return day_status[0]

        day_status = DailyModuleStatus()
        day_status.created_at = day
        day_status.updated_at = day
        day_status.module = self
        day_status.statuses = self.status
        day_status.status = self.status
        day_status.site_config = self.site_config
        day_status.save()

        memcache.set(MODULE_DAY_STATUS_KEY % (day.month, day.day, self.id), day_status)
        return day_status

    def authenticate(self, api, secret):
        if self.site_config.api_key == api and \
            self.site_config.api_secret == secret:
            return True
        return False

    def __unicode__(self):
        return "%s - %s - %s" % (self.name, self.module_type, self.host)


class ScheduledMaintenance(models.Model):
    created_at = models.DateTimeField(null=True, blank=True, default=None)
    updated_at = models.DateTimeField(null=True, blank=True, default=None)
    status = models.CharField(max_length=30, choices=STATUS)
    time_estimate = models.IntegerField(default=0, help_text="Used units: minutes")
    scheduled_to = models.DateTimeField(null=True, blank=True, default=None)
    total_downtime = models.FloatField(default=0.0)
    message = models.TextField()
    module = models.ForeignKey('main.Module')
    site_config = models.ForeignKey('main.SiteConfig', null=True)

    @property
    def estimated_end_time(self):
        return self.scheduled_to + datetime.timedelta(minutes=self.time_estimate)

    @property
    def time_left(self):
        if self.is_in_the_future:
            return self.time_estimate
        if self.is_undergoing:
            return (self.estimated_end_time - datetime.datetime.now()).total_seconds() / 60
        return 0

    @property
    def is_in_the_future(self):
        return datetime.datetime.now() < self.scheduled_to

    @property
    def is_undergoing(self):
        now = datetime.datetime.now()
        return self.scheduled_to < now < self.estimated_end_time

    @property
    def is_done(self):
        return datetime.datetime.now() > self.estimated_end_time

    @property
    def status_img(self):
        return status_img(self.status)
    
    def __unicode__(self):
        return _('Scheduled to %s. Estimate of %s minutes.') % (self.scheduled_to,
                                                             self.time_estimate)

class TwitterAccount(models.Model):
    login = models.CharField(max_length=100)
    api_key = models.CharField(max_length=100)
    api_secret = models.CharField(max_length=100)
    post_tweet_automatically = models.BooleanField(default=False) # send tweet on status change
    monitor_stream = models.BooleanField(default=False) # show the strem monitor
    monitor_stream_terms = models.TextField() # terms to look for on the stream
    
    def __unicode__(self):
        return '@%s' % self.login


class UserProfile(models.Model):
    user = models.OneToOneField(User)

    # adding aditional fields to the user profile
    birth_date = models.DateField(_('Date of birth'), null=True, blank=True,
                                    help_text="Date format: YYYY-mm-dd")
    address = models.CharField(_('Address'), max_length=100, null=True, blank=True)
    city = models.CharField(_('City'), max_length=50, null=True, blank=True)
    country = models.CharField(_('Country'), max_length=50, null=True, blank=True)
    state = models.CharField(_('State'), max_length=50, null=True, blank=True)
    phone_number = models.CharField(_('Phone number'), max_length=15, null=True, blank=True)

    def __unicode__(self):
        return "%s (%s)" % (self.user.username, self.user.email)


def create_user_profile(sender, instance, created, **kwargs):
    if created:
        UserProfile.objects.create(user=instance)

post_save.connect(create_user_profile, sender=User)
