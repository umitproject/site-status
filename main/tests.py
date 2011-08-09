import os
import re
import unittest

from google.appengine.api import memcache
from google.appengine.ext import db
from google.appengine.ext import testbed
from google.appengine.api import apiproxy_stub_map

from django.test import TestCase
from django.test.client import Client
from django.core.urlresolvers import reverse
from django.contrib.auth.models import User

from main.models import *
from status_cron.views import CHECK_NOTIFICATION_KEY

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
        
        # Task stub fix
        taskqueue_stub = apiproxy_stub_map.apiproxy.GetStub( 'taskqueue' ) 
        dircontainingqueuedotyaml = os.path.dirname(os.path.dirname( __file__ ))
        taskqueue_stub._root_path = dircontainingqueuedotyaml
        
        self._create_passive_test_modules()
        self._create_active_test_modules()
        self._create_admin()
    
    def tearDown(self):
        self.testbed.deactivate()
        
    def _create_admin(self):
        user = User.objects.create_user('admin', 'whatever@whatever.wha', 'test')
        user.is_staff = True
        user.is_superuser = True
        user.save()
    
    def _login_as_admin(self):
        self.client.login(username='admin', password='test')
    
    def _create_passive_test_modules(self):
        self.passive_sane_module = Module()
        self.passive_sane_module.monitoring_since = datetime.datetime.now()
        self.passive_sane_module.updated_at = datetime.datetime.now()
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
        self.passive_insane_module.monitoring_since = datetime.datetime.now()
        self.passive_insane_module.updated_at = datetime.datetime.now()
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
        self.active_sane_module.monitoring_since = datetime.datetime.now()
        self.active_sane_module.updated_at = datetime.datetime.now()
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
        self.active_insane_module.monitoring_since = datetime.datetime.now()
        self.active_insane_module.updated_at = datetime.datetime.now()
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
    
    def test_populate_view(self):
        response = self.client.post(reverse('test_populate'))
        self.assertEqual(response.status_code, 200)
    
    def test_system_subscribe(self):
        self._test_subscription('test@umitproject.org', 'system', False)
    
    def _test_subscription(self, email, notification_type, one_time):
        # TODO: Totally remake this test to fit new scalable notification system.
        # TODO3: Gotta confirm the cron job can handle a huge number of notifications at a time (1000)
        # TODO4: Gotta confirm the time necessary to send one notification (task execution time) with a large number of recipients (100)
        # TODO5: Expose these tests to have them ran through the production server (admin only, of course)
        
        response = None
        event = self._create_open_event()
        target_id = None
        
        if notification_type == 'system':
            response = self.client.post(reverse('system_subscribe'),
                                        {'email':email,
                                         'one_time':one_time})
        elif notification_type == 'event':
            target_id = event.id
            response = self.client.post(reverse('event_subscribe',
                                                kwargs={'event_id':target_id}),
                                        {'email':email,
                                         'one_time':one_time})
        elif notification_type == 'module':
            target_id = event.module.id
            response = self.client.post(reverse('module_subscribe',
                                                kwargs={'module_id':target_id}),
                                        {'email':email,
                                         'one_time':one_time})
        else:
            raise Exception('Unknown notification_type: %s' % notification_type)
        
        self.assertEqual(response.status_code, 200)
        self.assertTrue(re.findall('.*?(successfuly subscribed).*?', response.content))
        
        # Checking if exists and if it isn't duplicated
        subscriber = Subscriber.objects.get(email=email)
        
        notification = NotifyOnEvent.objects.get(notification_type=notification_type,
                                                 target_id=target_id, one_time=one_time)
        self.assertTrue(subscriber.email in notification.list_emails)
        
        # Test one time notify behavior
        response = self.client.post(reverse('system_subscribe'), {'email':email, 'one_time':True})
        self.assertEqual(response.status_code, 200)
        self.assertTrue(re.findall('.*?(successfuly subscribed).*?', response.content))
        
        # Checking if exists and if it isn't duplicated
        subscriber = Subscriber.objects.get(email=email)
        
        notification = NotifyOnEvent.objects.filter(notification_type='system', one_time=True, target_id=None, last_notified=None)
        self.assertTrue(notification)
        notification = notification[0]
        
        # Check if email is there
        self.assertTrue(subscriber.email in notification.list_emails)
        
        # Now, test that once the system is back user is notified
        event.back_at = datetime.datetime.now()
        event.save()
        
        notification_event = Notification.objects.get(notification_type='event',
                                                      target_id=event.id,
                                                      sent_at=None)
        
        self._login_as_admin()
        response = self.client.get(reverse('check_notifications'))
        self.assertEqual(response.status_code, 200)
        
        # Check if task was scheduled
        not_key = CHECK_NOTIFICATION_KEY % notification_event.id
        self.assertTrue(memcache.get(not_key, False))
        
        # But since the stub won't work locally, we ought to call the task ourselves
        response = self.client.get(reverse('send_notification_task',
                                           kwargs={'notification_id':notification_event.id}))
        self.assertEqual(response.status_code, 200)
        
        notification = NotifyOnEvent.objects.filter(notification_type='system', one_time=True, target_id=None)
        self.assertTrue(notification)
        notification = notification[0]
        
        self.assertFalse(notification.last_notified == None)
    
    def _create_notification(self, notification_type, target_id, previous_status, current_status, downtime):
        notification = Notification()
        notification.created_at = datetime.datetime.now()
        notification.notification_type = notification_type
        notification.target_id = target_id
        notification.previous_status = previous_status
        notification.current_status = current_status
        notification.downtime = downtime
        notification.save()
    
        return notification
    
    def test_module_subscribe(self):
        pass
    
    def test_event_subscribe(self):
        pass
    
    def test_subscriber_creation(self):
        pass
    
    def test_unsubscription(self):
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
        self._login_as_admin()
        response = self.client.get(reverse('check_passive_hosts_task',
                                  kwargs=dict(module_key=module.id)))
        
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
        
        
