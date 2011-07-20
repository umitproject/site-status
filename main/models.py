#!/usr/bin/env python

import datetime
import logging

from django.db import models
from django.db.models.signals import post_save

from main.memcache import memcache

##########
# CHOICES
STATUS = (
          ('on-line', 'On-line'),
          ('off-line', 'Off-line'),
          ('smaintenance', 'Scheduled Maintenance'),
          ('maintenance', 'Maintenance'),
          ('read-only', 'Read-Only'),
          ('investigating', 'Investigating'),
          ('updating', 'Updating'),
          ('service_disruption', 'Service Disruption'),
          ('unknown', 'Unknown')
          )

MODULE_TYPES = (
                ('passive', 'Passive'),
                ('active', 'Active')
                )

################
# MEMCACHE KEYS
MODULE_TODAY_STATUS_KEY = 'module_today_status_%s'

class Subscribers(models.Model):
    '''Full list of all users who ever registered asking to be notified.
    Used for consultation on when was last time user accessed the status site
    or since when he is registered, as well as his email that is used as a key.
    '''
    created_at = models.DateTimeField(auto_now_add=True)
    last_notified = models.DateTimeField()
    last_access = models.DateTimeField()
    email = models.EmailField()
    
    def __unicode__(self):
        return self.email

class AlwaysNotifyOnEvent(models.Model):
    '''Aggregation for all users who asked to *ALWAYS* be notified when
    an event occours for a given site or module.
    '''
    created_at = models.DateTimeField(auto_now_add=True)
    last_notified = models.DateTimeField(auto_now=True)
    email = models.EmailField()
    
    def __unicode__(self):
        return self.email

class NotifyOnEvent(models.Model):
    '''Aggregation for all users who asked to be notified about an specific
    event only once (site is offline now, and she wants to be informed when
    it is back).
    '''
    email = models.EmailField()
    originating_ip = models.CharField(max_length='50')
    event = models.ForeignKey('main.ModuleEvent')
    notified = models.BooleanField(default=False)
    
    def __unicode__(self):
        return '%s %s' % (self.email,
                          'notified' if self.notified else 'not notified')

class AggregatedStatus(models.Model):
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    total_downtime = models.FloatField(default=0.0)
    time_estimate_all_modules = models.FloatField(default=0.0)
    status = models.CharField(max_length=30, choices=STATUS)
    
    @property
    def total_uptime(self):
        return (datetime.datetime.now() - \
                self.created_at).minutes - self.total_downtime
    
    @property
    def percentage_uptime(self):
        return (self.total_uptime()/100) * self.total_downtime
    
    @property
    def percentage_downtime(self):
        return 100.0 - self.percentage_uptime
    
    @property
    def availability(self):
        return self.percentage_uptime()
    
    def __unicode__(self):
        return 'Uptime: %s - Downtime: %s - Availability: %s%% - Status %s' % \
                        (self.total_uptime, self.total_downtime,
                         self.availability, self.status)

class DailyModuleStatus(models.Model):
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    total_downtime = models.FloatField(default=0.0) # minutes
    statuses = models.TextField()
    events = models.TextField()
    status = models.CharField(max_length=30, choices=STATUS)
    module = models.ForeignKey('main.Module')
    
    # TODO: on creation, revoke module's today_status memcache
    
    @property
    def total_uptime(self):
        return (24*60) - self.total_downtime
    
    @property
    def percentage_uptime(self):
        return (self.total_uptime()/100) * self.total_downtime
    
    @property
    def percentage_downtime(self):
        return 100.0 - self.percentage_uptime
    
    def __unicode__(self):
        return '%s (%s) had a total downtime %.2d on %s' % (self.module.name,
                                                          self.status,
                                                          self.total_downtime,
                                                          self.created_at)

class ModuleEvent(models.Model):
    down_at = models.DateTimeField(auto_now_add=True)
    back_at = models.DateTimeField()
    details = models.TextField()
    status = models.CharField(max_length=30, choices=STATUS)
    module = models.ForeignKey('main.Module')
    
    @property
    def total_downtime(self):
        '''Returns total downtime in seconds
        '''
        if self.back_at:
            return float((self.back_at - self.down_at).seconds / 60.0)
        else:
            return float((datetime.datetime.now() - self.down_at).seconds / 60.0)
    
    def __unicode__(self):
        if self.back_at:
            return '%s (%s) for %.2d minutes' % (self.module.name,
                                                 self.status,
                                                 self.total_downtime)
        else:
            return '%s (%s) since %.2d' % (self.module.name,
                                           self.status,
                                           self.down_at)

#####################
# ModuleEvent signals
def module_event_post_save(sender, instance, created, **kwargs):
    if created:
        instance.module.status = instance.status
    
    if instance.back_at:
        instance.module.status = 'on-line'
        
        day_status = instance.module.today_status
        day_status.statuses = "%s,%s" % (day_status.statuses,
                                         instance.module.status)
        
        if instance.module.status:
            day_status.status = instance.module.status
        else:
            day_status.status = 'unknown'
        
        day_status.events = "%s,%s" % (day_status.events,
                                       instance.id)
        day_status.statuses = "%s,%s" % (day_status.statuses,
                                         instance.status)
        
        day_status.total_downtime += event.total_downtime
        
        day_status.save()
    
    instance.module.save()

post_save.connect(module_event_post_save, sender=ModuleEvent)


class Module(models.Model):
    monitoring_since = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    name = models.CharField(max_length=50)
    description = models.TextField()
    total_downtime = models.FloatField(default=0.0)
    module_type = models.CharField(max_length=15, choices=MODULE_TYPES) # two initial types: passive and active. In passive, status site pings the url to see if it returns 200. In the active mode, the server sends message to status site to inform its status
    host = models.CharField(max_length=500)
    url = models.CharField(max_length=1000)
    status = models.CharField(max_length=30, choices=STATUS) # current_status
    api_key = models.CharField(max_length=100)
    api_secret = models.CharField(max_length=100)
    
    @property
    def total_uptime(self):
        return ((datetime.datetime.now() - \
                 self.monitoring_since).seconds / 60) - self.total_downtime
    
    @property
    def percentage_uptime(self):
        return (self.total_uptime()/100) * self.total_downtime
    
    @property
    def percentage_downtime(self):
        return 100.0 - self.percentage_uptime
    
    @property
    def last_7_days(self):
        return DailyModuleStatus.objects.filter(module=self).\
                                        order_by('created_at')[:7]
    
    @property
    def today_status(self):
        today_status = memcache.get(MODULE_TODAY_STATUS_KEY % self.id, False)
        
        today = datetime.datetime.now()
        if today_status and \
                (today_status.created_at.day == now.day and \
                 today_status.created_at.month == now.month and \
                 today_status.created_at.year == now.year):
            # Return an actual today status
            return today_status
        
        today_status = DailyModuleStatus.objects.\
                        filter(module=self).\
                        filter(created_at__gte=datetime.datetime(\
                                 day.year, day.month, day.day, 0, 0, 0)).\
                        filter(created_at__lte=datetime.datetime(\
                                 day.year, day.month, day.day, 23, 59, 59, 999999))

        if today_status:
            memcache.set(MODULE_TODAY_STATUS_KEY * self.id, today_status)
            return today_status
        
        today_status = DailyModuleStatus()
        today_status.module = self
        today_status.statuses = self.status
        today_status.status = self.status
        today_status.save()
        
        memcache.set(MODULE_TODAY_STATUS_KEY * self.id, today_status)
        return today_status

    def __unicode__(self):
        return "%s - %s - %s" % (self.name, self.module_type, self.host)

class ScheduledMaintenance(models.Model):
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    status = models.CharField(max_length=30, choices=STATUS)
    time_estimate = models.IntegerField(default=0)
    scheduled_to = models.DateTimeField()
    total_downtime = models.FloatField(default=0.0)
    message = models.TextField()
    module = models.ForeignKey('main.Module')
    
    def __unicode__(self):
        return 'Scheduled to %s. Estimate of %s minutes.' % (self.scheduled_to,
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


singleton_twitter_account = TwitterAccount.objects.all()[:1]

def twitter_account():
    global singleton_twitter_account
    
    if singleton_twitter_account:
        return singleton_twitter_account
    
    singleton_twitter_account = TwitterAccount.objects.all()[:1]
    return singleton_twitter_account
