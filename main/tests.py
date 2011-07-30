
import unittest
from google.appengine.api import memcache
from google.appengine.ext import db
from google.appengine.ext import testbed

from django.test import TestCase
from django.test.client import Client
from django.core.urlresolvers import reverse

from main.models import *

class TestSiteStatus(TestCase):
    def setUp(self):
        # This is necessary to test datastore and memcache
        self.testbed = testbed.Testbed()
        self.testbed.activate()
        self.testbed.init_datastore_v3_stub()
        self.testbed.init_memcache_stub()
        
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
        pass
    
    def test_module_methods(self):
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
        
        
