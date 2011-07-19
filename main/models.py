#!/usr/bin/env python

import datetime
import logging

from django.db import models
from django.db.models.signals import post_save

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

class Subscribers(models.Model):
    '''Full list of all users who ever registered asking to be notified.
    Used for consultation on when was last time user accessed the status site
    or since when he is registered, as well as his email that is used as a key.
    '''
    created_at = models.DateTimeField(auto_now_add=True)
    last_notified = models.DateTimeField()
    last_access = models.DateTimeField()
    email = models.EmailField()

class AlwaysNotifyOnEvent(models.Model):
    '''Aggregation for all users who asked to *ALWAYS* be notified when
    an event occours for a given site or module.
    '''
    created_at = models.DateTimeField(auto_now_add=True)
    last_notified = models.DateTimeField(auto_now=True)
    email = models.EmailField()

class NotifyOnEvent(models.Model):
    '''Aggregation for all users who asked to be notified about an specific
    event only once (site is offline now, and she wants to be informed when
    it is back).
    '''
    email = models.EmailField()
    originating_ip = models.CharField(max_length='50')
    event = models.ForeignKey('main.ModuleEvent')
    notified = models.BooleanField(default=False)

class AggregatedStatus(models.Model):
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    total_uptime = models.FloatField(default=0.0)
    total_downtime = models.FloatField(default=0.0)
    current_availability = models.FloatField(default=0.0)
    time_estimate_all_modules = models.FloatField(default=0.0)
    current_status = models.CharField(max_length=30, choices=STATUS)

class DailyModuleStatus(models.Model):
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    total_downtime = models.FloatField(default=0.0) # minutes
    statuses = models.TextField()
    events = models.TextField()
    status = models.CharField(max_length=30, choices=STATUS)
    module = models.ForeignKey('main.Module')
    
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
            return '%s (%s) for %.2d minutes' % (self.module.name, self.status, self.total_downtime)
        else:
            return '%s (%s) since %.2d' % (self.module.name, self.status, self.down_at)

#####################
# ModuleEvent signals
def module_event_post_save(sender, instance, created, **kwargs):
    if created:
        instance.module.status = instance.status
    elif instance.back_at:
        instance.module.status = 'on-line'

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
    
    def aggregate_daily_status(self, day=datetime.date.today(), events=None):
        if events is None:
            events = ModuleEvent.objects.\
                            filter(down_at__gte=datetime.datetime(day.year,
                                            day.month, day.day, 0, 0, 0)).\
                            filter(down_at__lte=datetime.datetime(day.year,
                                            day.month, day.day, 23, 59, 59, 999999)).\
                            order_by('down_at')
        
        day_status = DailyModuleStatus.objects.\
                        filter(created_at__gte=datetime.datetime(day.year,
                                        day.month, day.day, 0, 0, 0)).\
                        filter(created_at__lte=datetime.datetime(day.year,
                                        day.month, day.day, 23, 59, 59, 999999))
        if not day_status:
            day_status = DailyModuleStatus()
            day_status.module = self
            day_status.statuses = self.status
        else:
            day_status = day_status[0]
            day_status.statuses = "%s,%s" % (day_status.statuses, self.status)
        
        if self.status:
            day_status.status = self.status
        else:
            day_status.status = 'unknown'
        
        current_events = day_status.events.split(',')
        
        for event in events: 
            if event.id not in current_events and event.back_at:
                day_status.statuses = "%s,%s" % (day_status.statuses, event.status)
                day_status.events = "%s,%s" % (day_status.events, event.id)
                day_status.total_downtime += event.total_downtime
                
        day_status.save()
        
        return day_status

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

class TwitterAccount(models.Model):
    login = models.CharField(max_length=100)
    api_key = models.CharField(max_length=100)
    api_secret = models.CharField(max_length=100)
    post_tweet_automatically = models.BooleanField(default=False) # send tweet on status change
    monitor_stream = models.BooleanField(default=False) # show the strem monitor
    monitor_stream_terms = models.TextField() # terms to look for on the stream
