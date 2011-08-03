
import unittest
from google.appengine.api import memcache
from google.appengine.ext import db
from google.appengine.ext import testbed

from django.test import TestCase
from django.test.client import Client
from django.core.urlresolvers import reverse

from main.models import *

class TestSiteStatus(TestCase):
    def __init__(self, *args, **kwargs):
        super(TestSiteStatus, self).__init__(*args, **kwargs)
    
    def setUp(self):
        # This is necessary to test datastore and memcache
        self.testbed = testbed.Testbed()
        self.testbed.activate()
        self.testbed.init_datastore_v3_stub()
        self.testbed.init_memcache_stub()
        
        # Create global aggregation entry.
        self.aggregation = AggregatedStatus()
        self.aggregation.created_at = datetime.datetime.now() - datetime.timedelta(days=10)
        self.aggregation.updated_at = self.aggregation.created_at
        self.aggregation.save()
        
        self._create_passive_test_modules()
        self._create_active_test_modules()
    
    def tearDown(self):
        self.testbed.deactivate()
    
    def _create_passive_test_modules(self):
        self.passive_sane_module = Module()
        self.passive_sane_module.name = 'Umit Project'
        self.passive_sane_module.description = 'This is the sane module being tested.'
        self.passive_sane_module.module_type = 'passive'
        self.passive_sane_module.host = 'www.google.com'
        self.passive_sane_module.url = 'http://www.google.com'
        self.passive_sane_module.status = 'unknown' # unknown is the default starting status for any module
        self.passive_sane_module.api_key = 'kjh'
        self.passive_sane_module.api_secret = 'ouiopu'
        self.passive_sane_module.save()
        
        self.passive_insane_module = Module()
        self.passive_insane_module.name = 'Freako'
        self.passive_insane_module.description = 'This is the insane module being tested.'
        self.passive_insane_module.module_type = 'passive'
        self.passive_insane_module.host = 'weird.weird.o'
        self.passive_insane_module.url = 'http://weird.weird.o'
        self.passive_insane_module.status = 'unknown' # unknown is the default starting status for any module
        self.passive_insane_module.api_key = 'iuewryt'
        self.passive_insane_module.api_secret = 'kjzxhf'
        self.passive_insane_module.save()
    
    def _create_active_test_modules(self):
        self.active_sane_module = Module()
        self.active_sane_module.name = 'Umit Project'
        self.active_sane_module.description = 'This is the sane module being tested.'
        self.active_sane_module.module_type = 'active'
        self.active_sane_module.host = 'www.google.com'
        self.active_sane_module.url = 'http://www.google.com'
        self.active_sane_module.status = 'unknown' # unknown is the default starting status for any module
        self.active_sane_module.api_key = 'kjh'
        self.active_sane_module.api_secret = 'ouiopu'
        self.active_sane_module.save()
        
        self.active_insane_module = Module()
        self.active_insane_module.name = 'Freako'
        self.active_insane_module.description = 'This is the insane module being tested.'
        self.active_insane_module.module_type = 'active'
        self.active_insane_module.host = 'weird.weird.o'
        self.active_insane_module.url = 'http://weird.weird.o'
        self.active_insane_module.status = 'unknown' # unknown is the default starting status for any module
        self.active_insane_module.api_key = 'iuewryt'
        self.active_insane_module.api_secret = 'kjzxhf'
        self.active_insane_module.save()
    
    def test_daily_module_status_automatic_creation(self):
        pass
    
    def test_event_creation_signal(self):
        event = self._create_open_event()
        
        # Event is open, so only the first part of it should be completed by now. Let's check:
        module = event.module
        day_status = module.get_day_status(event.down_at)
        aggregation = AggregatedStatus.objects.all()[0]
        
        self.assertEqual(module.status, event.status)
        self.assertEqual(day_status.status, event.status)
        self.assertEqual(aggregation.status, event.status)
        
        event.back_at = datetime.datetime.now()
        event.save()
        
        # Event is now over, so only the last part of the signal should be completed by now. Checking...
        # PS: Gotta reload data from datastore
        module = Module.objects.get(pk=module.pk)
        day_status = DailyModuleStatus.objects.get(pk=day_status.pk)
        aggregation = AggregatedStatus.objects.all()[0]
        
        self.assertEqual(module.status, 'on-line')
        self.assertEqual(day_status.status, 'on-line')
        self.assertEqual(aggregation.status, 'on-line')
        
        self.assertEqual(aggregation.total_downtime, 60)
        self.assertEqual(day_status.total_downtime, 60)
        self.assertEqual(module.total_downtime, 60)
    
    def test_module_methods(self):
        pass
    
    def _create_60_min_event(self):
        now = datetime.datetime.now()
        hour_ago = now - datetime.timedelta(minutes=60)
        
        event = ModuleEvent()
        event.module = self.passive_sane_module
        event.down_at = hour_ago
        event.back_at = now
        event.status = 'service_disruption'
        event.save()
        
        return event
    
    def _create_open_event(self):
        hour_ago = datetime.datetime.now() - datetime.timedelta(minutes=60)
        
        event = ModuleEvent()
        event.module = self.passive_sane_module
        event.down_at = hour_ago
        event.status = 'service_disruption'
        event.save()
        
        return event
        
    def test_availability_accuracy(self):
        event = self._create_60_min_event()
        
        self.assertEqual(event.total_downtime, 60)
        
        aggregation = AggregatedStatus.objects.all()[0]
        
        self.assertEqual(aggregation.total_downtime, 60)
        self.assertEqual(aggregation.total_uptime, 14340)
        self.assertTrue(aggregation.percentage_uptime > 99)
        self.assertEqual(aggregation.status, 'on-line')
    
    def test_aggregation_status(self):
        event = self._create_open_event()

        self.assertEqual(event.total_downtime, 60)
        
        aggregation = AggregatedStatus.objects.all()[0]
        self.assertEqual(aggregation.status, 'service_disruption')
        
        event.back_at = datetime.datetime.now()
        event.save()
        
        aggregation = AggregatedStatus.objects.all()[0]
        self.assertEqual(aggregation.status, 'on-line')
        
        self.assertEqual(aggregation.total_downtime, 60)
        self.assertEqual(aggregation.total_uptime, 14340)
        self.assertTrue(aggregation.percentage_uptime > 99)
    
    def test_uptime_graph_accuracy(self):
        event = self._create_60_min_event()
        num_modules = Module.objects.count()
        
        aggregation = AggregatedStatus.objects.all()[0]
        today = '%s/%s' % (event.down_at.month, event.down_at.day)
        
        for up in aggregation.uptime_data:
            if up[0] == today:
                self.assertEqual(up[1], 100.0 - percentage(event.total_downtime, 24*60*num_modules))
            else:
                self.assertEqual(up[1], 100)
    
    def test_incidents_graph_accuracy(self):
        event = self._create_60_min_event()
        num_modules = Module.objects.count()
        
        aggregation = AggregatedStatus.objects.all()[0]
        today = '%s/%s' % (event.down_at.month, event.down_at.day)
        
        for inc in aggregation.incidents_data:
            if inc[0] == today:
                self.assertEqual(inc[1], percentage(event.total_downtime, 24*60*num_modules))
            else:
                self.assertEqual(inc[1], 0)
    
    def test_feeds(self):
        pass
    
    def test_event_view(self):
        pass
    
    def _test_passive_module(self, module, right_status, right_statuses, right_list_statuses):
        c = Client()
        response = c.get(reverse('check_passive_hosts_task',
                                  kwargs=dict(module_key=module.id)),
                         follow=True)
        
        self.assertEqual(response.status_code, 200)
        
        module = Module.objects.get(id=module.id)
        
        # Check if status became on-line for it
        self.assertEqual(module.status, right_status)
        
        # Check if daily status shows both status
        statuses = module.today_status.unique_statuses
        if statuses != right_statuses:
            raise Exception("Daily status doesn't show the proper statuses: %s. Should be %s" % (statuses, right_statuses))
        
        # Check if daily status return a sane list_statuses
        list_statuses = module.today_status.list_statuses
        if list_statuses != right_list_statuses:
            raise Exception("Daily status doesn't show the proper list_statuses: %s. Should be %s" % (list_statuses, right_list_statuses))
        
        # Check if there is an event for the initial unknown status
        try:
            event = ModuleEvent.objects.get(module=module.id)
            self.assertEqual(event.status, 'unknown')
        except ModuleEvent.DoesNotExist, e:
            logging.critical('There is no ModuleEvent linked to %s with id %s' % (module, module.id))
            logging.critical('All module events: %s' % ModuleEvent.objects.all())
            raise e
        
        # Check if daily status is linking properly to the event record
        self.assertEqual(module.today_status.events, str(event.id))
        
    def test_passive_hosts_check(self):
        #######################
        # SANE PASSIVE MODULE
        self._test_passive_module(self.passive_sane_module, 'on-line', ['unknown', 'on-line'],
                                  [['unknown', 'img/unknown.gif'], ['on-line', 'img/on-line.gif']])
        
        #######################
        # INSANE PASSIVE MODULE
        self._test_passive_module(self.passive_insane_module, 'unknown', ['unknown'],
                                  [['unknown', 'img/unknown.gif']])
        
        
