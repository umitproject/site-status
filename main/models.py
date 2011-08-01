#!/usr/bin/env python

import datetime
import logging

from django.db import models
from django.db.models.signals import post_save, pre_save
from django.template.loader import render_to_string

from main.memcache import memcache
from main.utils import pretty_date

############
# CONSTANTS
SHOW_DAYS = 7 # amount of days to show in main page

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
MODULE_DAY_STATUS_KEY = 'module_day_status_%s_%s__%s'


###################
# Helper Functions

def status_img(status):
    return 'img/%s.gif' % status

def verbose_status(status):
    return dict(STATUS)[status]

def timedelta_seconds(delta):
    return (delta.days * 24 * 60 * 60) + delta.seconds + (delta.microseconds/1000000)

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
    status = models.CharField(max_length=30, choices=STATUS, default=STATUS[0][0])
    
    @property
    def total_uptime(self):
        now = datetime.datetime.now()
        uptime = (timedelta_seconds(now - self.created_at) / 60.0) - self.total_downtime
        return uptime if uptime > self.total_downtime else 0.0
    
    @property
    def percentage_uptime(self):
        return 100.0 - self.percentage_downtime
    
    @property
    def percentage_downtime(self):
        return ((self.total_downtime * 100.0) / self.total_uptime) if self.total_uptime > 0 else 100.0

    @property
    def incidents_data(self):
        today = datetime.datetime.now()
        
        incidents = []
        for d in xrange(6, -1, -1):
            incident = []
            day = today - datetime.timedelta(days=d)
            
            data = ModuleEvent.objects.\
                        filter(down_at__gte=datetime.datetime(\
                                 day.year, day.month, day.day, 0, 0, 0)).\
                        filter(down_at__lte=datetime.datetime(\
                                 day.year, day.month, day.day, 23, 59, 59, 999999))
        
            key = '%s/%s' % (day.month, day.day)
            if data:
                for d in data:
                    if key in incident:
                        incident[1] += d.total_downtime
                    else:
                        incident = [key, d.total_downtime]
            else:
                incident = [key, 0]
            
            incidents.append(incident)
                    
        return incidents

    @property
    def uptime_data(self):
        today = datetime.datetime.now()
        num_modules = Module.objects.count()
        
        uptimes = []
        for d in xrange(6, -1, -1):
            uptime = []
            day = today - datetime.timedelta(days=d)
            
            data = DailyModuleStatus.objects.\
                        filter(created_at__gte=datetime.datetime(\
                                 day.year, day.month, day.day, 0, 0, 0)).\
                        filter(created_at__lte=datetime.datetime(\
                                 day.year, day.month, day.day, 23, 59, 59, 999999))
        
            key = '%s/%s' % (day.month, day.day)
            if data:
                for d in data:
                    if key in uptime:
                        uptime[1] += d.total_uptime
                    else:
                        uptime = [key, d.total_uptime]
            else:
                uptime = [key, 24*60*num_modules]
            
            uptimes.append(uptime)
        
        return uptimes
    
    @property
    def last_incident(self):
        last_incident = ModuleEvent.objects.all().order_by('-down_at')[:1]
        if last_incident:
            last_incident = last_incident[0]
        
        return last_incident
    
    def __unicode__(self):
        return 'Uptime: %s - Downtime: %s - Availability: %s%% - Status %s' % \
                        (self.total_uptime, self.total_downtime,
                         self.availability, self.status)


class DailyModuleStatus(models.Model):
    created_at = models.DateTimeField()
    updated_at = models.DateTimeField(blank=True, null=True)
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
    
    def add_status(self, status):
        if status is None:
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
        return '%s (%s) had a total downtime %.2d on %s' % (self.module.name,
                                                            self.status,
                                                            self.total_downtime,
                                                            self.created_at)
class ModuleEvent(models.Model):
    down_at = models.DateTimeField()
    back_at = models.DateTimeField(blank=True, null=True)
    details = models.TextField()
    status = models.CharField(max_length=30, choices=STATUS)
    module = models.ForeignKey('main.Module')
    
    @property
    def total_downtime(self):
        '''Returns total downtime in seconds
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
        logging.critical('>>> Verbose HTML: %s' % str(context))
        return render_to_string('parts/last_incident.html', context) 
    
    @property
    def verbose(self):
        return ''
    
    def __unicode__(self):
        if self.back_at:
            return '%s (%s) for %.2d minutes' % (self.module.name,
                                                 self.status,
                                                 self.total_downtime)
        else:
            return '%s (%s) since %s:%s' % (self.module.name,
                                           self.status,
                                           self.down_at.hour,
                                           self.down_at.minute)

######################
# ModuleEvent signals
def module_event_post_save(sender, instance, created, **kwargs):
    day_status = instance.module.get_day_status(instance.down_at)
    day_status.add_event(instance.id)
    
    if created:
        instance.module.status = instance.status
        day_status.add_status(instance.status)
    
    if instance.back_at:
        instance.module.status = 'on-line'
        day_status.add_status(instance.module.status)
        
        day_status.total_downtime += instance.total_downtime
        
        aggregation = AggregatedStatus.objects.all()[0]
        aggregation.total_downtime += instance.total_downtime
        aggregation.save()
    
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
    
    @staticmethod
    def show_days(days=None):
        modules = Module.objects.all()
        show_days = SHOW_DAYS
        
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
    def total_uptime(self):
        return (timedelta_seconds(datetime.datetime.now() - \
                 self.monitoring_since) / 60) - self.total_downtime
    
    @property
    def percentage_uptime(self):
        return (self.total_uptime()/100) * self.total_downtime
    
    @property
    def percentage_downtime(self):
        return 100.0 - self.percentage_uptime
    
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
                                 day.year, day.month, day.day, 23, 59, 59, 999999))

        if day_status:
            memcache.set(MODULE_DAY_STATUS_KEY % (day.month, day.day, self.id), day_status[0])
            return day_status[0]
        
        day_status = DailyModuleStatus()
        day_status.created_at = day
        day_status.updated_at = day
        day_status.module = self
        day_status.statuses = self.status
        day_status.status = self.status
        day_status.save()
        
        memcache.set(MODULE_DAY_STATUS_KEY % (day.month, day.day, self.id), day_status)
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
if not singleton_twitter_account:
    singleton_twitter_account = None

singleton_aggregated_status = AggregatedStatus.objects.all()[:1]
if not singleton_aggregated_status:
    singleton_aggregated_status = AggregatedStatus()
    singleton_aggregated_status.save()


def twitter_account():
    global singleton_twitter_account
    
    if singleton_twitter_account:
        return singleton_twitter_account
    
    singleton_twitter_account = TwitterAccount.objects.all()[:1]
    return singleton_twitter_account
