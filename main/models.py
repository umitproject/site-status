from django.db import models

STATUS = (
          ('online', 'On-line'),
          ('offline', 'Off-line'),
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
    total_uptime = models.FloatField(default=0.0)
    total_downtime = models.FloatField(default=0.0)
    statuses = models.TextField()
    status = models.CharField(max_length=30, choices=STATUS)
    module = models.ForeignKey('main.Module')

class ModuleEvent(models.Model):
    down_at = models.DateTimeField(auto_now_add=True)
    status = models.CharField(max_length=30, choices=STATUS)
    module = models.ForeignKey('main.Module')

class Module(models.Model):
    updated_at = models.DateTimeField(auto_now=True)
    name = models.CharField(max_length=50)
    description = models.TextField()
    total_uptime = models.FloatField(default=0.0)
    total_downtime = models.FloatField(default=0.0)
    module_type = models.CharField(max_length=15, choices=MODULE_TYPES) # two initial types: passive and active. In passive, status site pings the url to see if it returns 200. In the active mode, the server sends message to status site to inform its status
    host = models.CharField(max_length=500)
    url = models.CharField(max_length=1000)
    current_status = models.CharField(max_length=30, choices=STATUS)
    
    def last_7_days(self):
        return DailyModuleStatus.objects.filter(module=self).order('created_at')[:7]

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
