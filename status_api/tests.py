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

from google.appengine.api import memcache
from google.appengine.ext import db
from google.appengine.ext import testbed
from google.appengine.api import apiproxy_stub_map

from django.test import TestCase
from django.core.urlresolvers import reverse
from django.contrib.auth.models import User

from main.models import *

class TestStatusApi(TestCase):
    def __init__(self, *args, **kwargs):
        super(TestStatusApi, self).__init__(*args, **kwargs)
    
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
    
    def test_report_status(self):
        pass
    
    def test_check_status(self):
        pass
    
    def test_check_downtime(self):
        pass
    
    def test_check_incidents(self):
        pass
    
    def test_check_uptime(self):
        pass
    
    def test_availability(self):
        pass