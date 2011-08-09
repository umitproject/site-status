#!/usr/bin/env python

import datetime
import logging
from decimal import *
import uuid
from types import StringTypes
import itertools

from django.db import models
from django.db.models.signals import post_save, pre_save
from django.template.loader import render_to_string
from django.conf import settings

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
          ('unknown', 'Unknown'),
          )

MODULE_TYPES = (
                ('passive', 'Passive'),
                ('active', 'Active'),
                )

NOTIFICATION_TYPES = (
                      ('module', 'Module'),
                      ('event', 'Event'),
                      ('system', 'System'),
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

def percentage(value, total):
    if type(value) not in StringTypes:
        value = '%.2f' % value
    if type(total) not in StringTypes:
        total = '%.2f' % total
    
    return round((Decimal(value) * Decimal(100)) / Decimal(total), 2)

class Subscriber(models.Model):
    '''Full list of all users who ever registered asking to be notified.
    Used for consultation on when was last time user accessed the status site
    or since when he is registered, as well as his email that is used as a key.
    '''
    unique_identifier = models.CharField(max_length=36, blank=True, null=True, default='')
    created_at = models.DateTimeField()
    updated_at = models.DateTimeField(null=True, blank=True, default=None)
    email = models.EmailField()
    subscriptions = models.TextField()
    originating_ips = models.TextField()
    unsubscribed_at = models.DateTimeField(null=True, blank=True, default=None)
    
    @property
    def list_subscriptions_ids(self):
        return [int(s) for s in self.subscriptions.split(',') if s != '']
    
    @property
    def list_subscriptions(self):
        return [NotifyOnEvent.objects.get(pk=int(s)) for s in self.subscriptions.split(',')]
    
    @property
    def list_ips(self):
        return self.originating_ips.split(',')
    
    def add_ip(self, ip):
        list_ips = self.list_ips
        if ip not in list_ips:
            list_ips.append(ip)
            self.originating_ips = ','.join(list_ips)
            return True
        return False
    
    def add_subscription(self, notification_id):
        subs_ids = self.list_subscriptions_ids
        if notification_id in subs_ids:
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
        return NotifyOnEvent.unsubscribe(self.email, notification_type, one_time, target_id)
    
    def subscribe(self, notification_type, one_time, target_id=None):
        notification = NotifyOnEvent.objects.filter(notification_type=notification_type,
                                                    one_time=one_time, target_id=target_id)
        
        if not notification:
            notification = NotifyOnEvent(created_at=datetime.datetime.now(),
                                         notification_type=notification_type,
                                         one_time=one_time, target_id=target_id) 
        
        notification.add_email(self.email)
        self.add_subscription(notification.id)
        
        self.save()
        notification.save()
        
        logging.critical('+++ Notif. %s, %s, %s' % (notification.notification_type, notification.one_time, notification.target_id))
        
        return notification
    
    def __unicode__(self):
        return self.email

class Notification(models.Model):
    """When an event happens, a notification is created.
    When a notification is created, the pre_save signal must go look for
    the relevant NotifyOnEvent instances and save the emails it will need
    to send out.
    """
    created_at = models.DateTimeField()
    sent_at = models.DateTimeField(null=True, blank=True, default=None)
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
    
    @property
    def list_emails(self):
        return [e for e in self.emails.split(',') if e]
    
    def build_email_data(self):
        target_url = settings.MAIN_SITE_URL
        target_name = settings.SITE_NAME
        
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
        self.body = render_to_string('parts/notification_body.txt', context)
        self.html = render_to_string('parts/notification_body.html', context)
    
    def save(self, *args, **kwargs):
        if not self.id:
            self._retrieve_emails()
        
        super(Notification, self).save(*args, **kwargs)
    
    def _notify_emails(self, notification_type, one_time, target_id):
        notify = None
        if one_time:
            notify = NotifyOnEvent.objects.filter(one_time=one_time,
                                                  notification_type=notification_type,
                                                  target_id=target_id,
                                                  last_notified=None)
        else:
            notify = NotifyOnEvent.objects.filter(one_time=one_time,
                                                  notification_type=notification_type,
                                                  target_id=target_id)
            
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

        notification_emails = [n.list_emails for n in notifications if n != []]
        
        emails = []
        for email in itertools.chain(*notification_emails):
            if email not in emails:
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
    created_at = models.DateTimeField()
    last_notified = models.DateTimeField(null=True, blank=True, default=None)
    one_time = models.BooleanField(default=False)
    notification_type = models.CharField(max_length=10, choices=NOTIFICATION_TYPES)
    target_id = models.IntegerField(null=True, blank=True, default=None)
    emails = models.TextField()
    
    @property
    def list_emails(self):
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
    
    @staticmethod
    def can_unsubscribe(email, notification_type, one_time, target_id=None):
        instance = NotifyOnEvent.objects.filter(notification_type=notification_type,
                                                one_time=one_time,
                                                target_id=target_id)
        if instance and email in instance.list_emails:
            return True
        return False
    
    @staticmethod
    def unsubscribe(email, notification_type, one_time, target_id=None):
        instance = NotifyOnEvent.objects.filter(notification_type=notification_type,
                                                one_time=one_time,
                                                target_id=target_id)
        list_emails = instance.list_emails
        if instance and email in list_emails:
            
            # Removing the NotifyOnEvent id from subscriber's instance
            subscriber = Subscriber.objects.get(email=email)
            
            subs_ids = subscriber.list_subscriptions_ids
            subs_ids.remove(instance.id)
            subscriber.subscriptions = ','.join(subs_ids)
            subscriber.save()
            
            # Removing subscriber's email from NotifyOnEvent instance
            if len(list_emails) == 1:
                instance.delete()
            else:
                list_emails.remove(email)
                instance.emails = ','.join(list_emails)
                instance.save()
            
            return True
        return False
    
    def __unicode__(self):
        return '%s (%s) - %s' % (self.notification_type, self.target_id,
                          'notified' if self.last_notified else 'not notified')


class AggregatedStatus(models.Model):
    created_at = models.DateTimeField()
    updated_at = models.DateTimeField(null=True, blank=True, default=None)
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
        return percentage(100, self.percentage_downtime)
    
    @property
    def percentage_downtime(self):
        return percentage(self.total_downtime * 100.0, self.total_uptime) if self.total_uptime > 0 else 100.0

    @property
    def incidents_data(self):
        today = datetime.datetime.now()
        total_base = Module.objects.count() * 24 * 60 # Total minutes all modules can be offline in a day
        
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
                    incident[1] = percentage(incident[1], total_base)
            else:
                incident = [key, 0]
            
            incidents.append(incident)
        
        return incidents

    @property
    def uptime_data(self):
        today = datetime.datetime.now()
        num_modules = Module.objects.count()
        total_base = num_modules * 24 * 60
        
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
                n = num_modules
                for d in data:
                    if key in uptime:
                        uptime[1] += d.total_uptime
                    else:
                        uptime = [key, d.total_uptime]
                    n -= 1
                else:
                    uptime[1] += 24*60*n
                    uptime[1] = percentage(uptime[1], total_base)
            else:
                uptime = [key, 100.0]
            
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
                         self.percentage_uptime, self.status)


class DailyModuleStatus(models.Model):
    created_at = models.DateTimeField()
    updated_at = models.DateTimeField(null=True, blank=True, default=None)
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
        return percentage(self.total_uptime, 24*60)
    
    @property
    def percentage_downtime(self):
        return percentage(self.total_downtime, self.total_uptime)
    
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
    back_at = models.DateTimeField(null=True, blank=True, default=None)
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
        return render_to_string('parts/last_incident.html', context) 
    
    @property
    def verbose(self):
        return "%(module)s (%(verbose_status)s) - %(verbose_time)s" % \
                    dict(module=self.module.name,
                         verbose_status=verbose_status(self.status),
                         verbose_time=pretty_date(self.down_at))
    
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
    
    aggregation = AggregatedStatus.objects.all()[0]
    
    if created:
        instance.module.status = instance.status
        day_status.add_status(instance.status)
        
        aggregation.status = instance.status
    
    if instance.back_at:
        instance.module.status = 'on-line'
        day_status.add_status(instance.module.status)
        
        day_status.total_downtime += instance.total_downtime
        instance.module.total_downtime += instance.total_downtime
        
        aggregation.total_downtime += instance.total_downtime
        
        # Sync aggregation status
        open_event = ModuleEvent.objects.filter(back_at=None).order_by('-down_at')[:1]
        if not open_event:
            aggregation.status = 'on-line'
        else:
            aggregation.status = open_event[0].status
        
        # Create notification
        notification = Notification()
        notification.created_at = datetime.datetime.now()
        notification.notification_type = 'event'
        notification.target_id = instance.id
        notification.previous_status = instance.status
        notification.current_status = 'on-line'
        notification.downtime = instance.total_downtime
        notification.save()
    
    aggregation.save()
    day_status.save()
    instance.module.save()

post_save.connect(module_event_post_save, sender=ModuleEvent)


class Module(models.Model):
    monitoring_since = models.DateTimeField()
    updated_at = models.DateTimeField(null=True, blank=True, default=None)
    name = models.CharField(max_length=50)
    description = models.TextField()
    total_downtime = models.FloatField(default=0.0)
    module_type = models.CharField(max_length=15, choices=MODULE_TYPES) # two initial types: passive and active. In passive, status site pings the url to see if it returns 200. In the active mode, the server sends message to status site to inform its status
    host = models.CharField(max_length=500)
    url = models.CharField(max_length=1000)
    status = models.CharField(max_length=30, choices=STATUS) # current_status
    tags = models.TextField(default="", blank=True, null=True)
    api_key = models.CharField(max_length=100)
    api_secret = models.CharField(max_length=100)
    
    @property
    def list_tags(self):
        return [tag.strip() for tag in self.tags.split(',')]
    
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
    created_at = models.DateTimeField()
    updated_at = models.DateTimeField(null=True, blank=True, default=None)
    status = models.CharField(max_length=30, choices=STATUS)
    time_estimate = models.IntegerField(default=0)
    scheduled_to = models.DateTimeField(null=True, blank=True, default=None)
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
