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

import os
import re
import unittest


from main.memcache import memcache

"""
from google.appengine.api import memcache
from google.appengine.ext import db
from google.appengine.ext import testbed
from google.appengine.api import apiproxy_stub_map
"""

from django.test import TestCase
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
        
        self.site_config = SiteConfig()
        self.site_config.site_name = "testserver"
        self.site_config.main_site_url = "testserver"
        self.site_config.save()
        
        status_domain = StatusSiteDomain()
        status_domain.status_url = "testserver"
        status_domain.site_config = self.site_config
        status_domain.save()
        
        # Create global aggregation entry.
        self.aggregation = AggregatedStatus()
        self.aggregation.created_at = datetime.datetime.now() - datetime.timedelta(days=10)
        self.aggregation.updated_at = self.aggregation.created_at
        self.aggregation.site_config = self.site_config
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
        self.passive_sane_module.site_config = self.site_config
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
        self.passive_insane_module.site_config = self.site_config
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
        self.active_sane_module.site_config = self.site_config
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
        self.active_insane_module.site_config = self.site_config
        self.active_insane_module.save()
    
    def test_daily_module_status_automatic_creation(self):
        pass    
    
    def test_populate_view(self):
        response = self.client.post(reverse('test_populate'))
        self.assertEqual(response.status_code, 200)
    
    def test_system_subscribe(self):
        self._test_subscription('test@umitproject.org', 'system', False)
        self._test_subscription('test@umitproject.org', 'system', True)
    
    def _test_subscription(self, email, notification_type, one_time):
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
                                                 target_id=target_id, one_time=one_time,
                                                 site_config=self.site_config)
        self.assertTrue(subscriber.email in notification.list_emails)
        
        # Now, test that once the system is back user is notified
        event.back_at = datetime.datetime.now()
        event.save()
        
        notification_event = Notification.objects.get(notification_type='event',
                                                      target_id=event.id,
                                                      sent_at=None,
                                                      site_config=self.site_config)
        
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
        
        notification = NotifyOnEvent.objects.get(notification_type=notification_type,
                                                 one_time=one_time, target_id=target_id,
                                                 site_config=self.site_config)
        
        if notification.last_notified == None:
            logging.critical('<<< Failing notification: %s' % notification)
        
        self.assertFalse(notification.last_notified == None)
    
    def test_module_subscribe(self):
        self._test_subscription('test@umitproject.org', 'module', False)
        self._test_subscription('test@umitproject.org', 'module', True)
    
    def test_event_subscribe(self):
        self._test_subscription('test@umitproject.org', 'event', True)
    
    def test_notification_task_sending_to_huge_amount_of_recipients(self):
        # TODO4: Gotta confirm the time necessary to send one notification
        #        (task execution time) with a large number of recipients (10000)
        email_mask = 'test+%s@umitproject.org'
        test_size = 50
        for i in xrange(test_size):
            response = self.client.post(reverse('system_subscribe'),
                                        {'email':email_mask % i,
                                         'one_time':False})
            self.assertEqual(response.status_code, 200)
        
        event = self._create_open_event()
        event.back_at = datetime.datetime.now()
        event.save()
        
        notification_event = Notification.objects.get(notification_type='event',
                                                      target_id=event.id,
                                                      sent_at=None)
        
        self._login_as_admin()
        start = datetime.datetime.now()
        response = self.client.get(reverse('send_notification_task',
                                           kwargs={'notification_id':notification_event.id}))
        end = datetime.datetime.now()
        
        logging.critical('>>> Time to process tasks on %s recipients: %s seconds' % (test_size, (end - start).seconds))
        
        self.assertEqual(response.status_code, 200)
        
        notification = NotifyOnEvent.objects.get(notification_type='system', one_time=False, target_id=None)
        
        if notification.last_notified == None:
            logging.critical('<<< Failing notification: %s' % notification)
        
        self.assertFalse(notification.last_notified == None)
        
    
    def test_notification_load(self):
        # TODO5: Expose these tests to have them ran through the production server (admin only, of course)
        
        # This is the amount of notifications the system should handle per minute
        # 8400 is equivalent to 140 notifications per second - This should be able
        # to run on virtually any robust setup.
        # If in somewhere else (other than appengine) this can scale even further,
        # and even in appengine can scale further if we make more than one cron
        # request per minute (totally possible).
        test_size = 50
        events = []
        notifications = []
        
        for i in xrange(test_size):
            events.append(self._create_open_event())
            
            # Setting the event back_at should create a notification 
            events[-1].back_at = datetime.datetime.now()
            events[-1].save()
            
            notifications.append(Notification.objects.get(notification_type='event',
                                                          target_id=events[-1].id,
                                                          sent_at=None))
        
        self.assertEqual(len(events), test_size)
        self.assertEqual(len(notifications), test_size)
        
        self._login_as_admin()
        
        # Now, we need to time the execution of the view.
        # If greater than 30 seconds, we're in danger of timeout
        start = datetime.datetime.now()
        response = self.client.get(reverse('check_notifications'))
        end = datetime.datetime.now()
        
        logging.critical('>>> Time to process %s: %s seconds' % (test_size, (end - start).seconds))
        
        # Check if it returned a 200. First indication that it succeeded
        self.assertEqual(response.status_code, 200)
        
        # Check the time it took to process everything is fewer than 30 secs
        self.assertTrue((end - start).seconds < 30)
        
        # Check if all tasks were scheduled properly
        for notification_event in notifications:
            not_key = CHECK_NOTIFICATION_KEY % notification_event.id
            self.assertTrue(memcache.get(not_key, False))
    
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
        event.site_config = self.site_config
        event.save()
        
        return event
    
    def _create_open_event(self):
        hour_ago = datetime.datetime.now() - datetime.timedelta(minutes=60)
        
        event = ModuleEvent()
        event.module = self.passive_sane_module
        event.down_at = hour_ago
        event.status = 'service_disruption'
        event.site_config = self.site_config
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
        
        
