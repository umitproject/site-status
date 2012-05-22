#!/usr/bin/env python
# -*- coding: utf-8 -*-
##
## Author: Adriano Marques <adriano@umitproject.org>
##
## Copyright (C) 2012 S2S Network Consultoria e Tecnologia da Informacao LTDA
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

# Initialize App Engine and import the default settings (DB backend, etc.).
# If you want to use a different backend you have to remove all occurences
# of "djangoappengine" from this file.
from djangoappengine.settings_base import *

import logging
import os
import sys

from os.path import join, dirname

sys.path.insert(0, join(dirname(__file__), 'djangoappengine', 'lib'))
sys.path.insert(0, join(dirname(__file__), 'lib'))


# Activate django-dbindexer for the default database
DATABASES['native'] = DATABASES['default']
DATABASES['default'] = {'ENGINE': 'dbindexer', 'TARGET': 'native',
                        'HIGH_REPLICATION': True}
AUTOLOAD_SITECONF = 'indexes'

SECRET_KEY = 'igaeofugq8fghrilbfrl3kh4h8ogdsdy1ohr;dpfgo87109ru;aokdhf;k'

DEBUG = True
TEMPLATE_DEBUG = DEBUG

ENVIRONMENT = os.environ.get('SERVER_SOFTWARE', 'GAETest')
GAE = True
PRODUCTION = True
TEST = False

if ENVIRONMENT == '':
    GAE = False
elif ENVIRONMENT.startswith('Development'):
    PRODUCTION = False
elif ENVIRONMENT.startswith('GAETest'):
    TEST = True
    PRODUCTION = False

# Set this to True, so you can run the test suite against local django,
# and False if you want to test against a live GAE instance.
# WARNING: Tests doesn't fully support this yet, because they don't setup
# the remote datastore properly
TEST_LOCAL = True
TEST_REMOTE_HTTP_HOST = "http://localhost:8000"


logging.info("Environment: '%s'" % ENVIRONMENT)

INSTALLED_APPS = (
    'django.contrib.admin',
    'django.contrib.contenttypes',
    'django.contrib.messages',
    'django.contrib.auth',
    'django.contrib.sessions',
    'registration',
    'djangotoolbox',
    'autoload',
    'dbindexer',
    'mediagenerator',
    'main',
    'status_cron',
    'status_api',
    'status_notification',
    'permission_backend_nonrel',

    # djangoappengine should come last, so it can override a few manage.py commands
    'djangoappengine',
    )


MIDDLEWARE_CLASSES = (
    # This loads the index definitions, so it has to come first
    'autoload.middleware.AutoloadMiddleware',

    # Media middleware needs to come first
    'mediagenerator.middleware.MediaMiddleware',

    'django.middleware.common.CommonMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'main.middleware.SubdomainMiddleware',
    'main.middleware.SiteConfigMiddleware',
    )

TEMPLATE_CONTEXT_PROCESSORS = (
    'django.contrib.auth.context_processors.auth',
    'django.core.context_processors.request',
    'django.core.context_processors.media',
    'django.contrib.messages.context_processors.messages',
    'main.context_processors.get_settings',
    )


# This test runner captures stdout and associates tracebacks with their
# corresponding output. Helps a lot with print-debugging.
TEST_RUNNER = 'djangotoolbox.test.CapturingTestSuiteRunner'

ADMIN_MEDIA_PREFIX = '/media/admin/'
TEMPLATE_DIRS = (os.path.join(os.path.dirname(__file__), 'templates'),)

ROOT_URLCONF = 'root_urls'
LOGIN_URL = '/accounts/login/'

CACHES = {
    'default': {
        'BACKEND': 'django.core.cache.backends.memcached.MemcachedCache',
        'TIMEOUT': 0,
        }
}

CACHE_MIDDLEWARE_SECONDS = 30
CACHE_METHOD_EXPIRATION = 300
CACHE_SHARDED_COUNTER_EXPIRATION = 30


#####################
# CURRENT STATUS BAR
DEFAULT_SHOW_INCIDENTS = True
DEFAULT_SHOW_UPTIME = True
DEFAULT_SHOW_LAST_INCIDENT = True

######################
# NOTIFICATION SYSTEM

NOTIFICATION_SYSTEM = 'courrier' # One of courrier or e-mail

COURRIER_CUSTOMER_KEY = ''
COURRIER_API_SECRET = ''
COURRIER_STATUS_CAMPAIGN_KEY = ""

DEFAULT_NOTIFICATION_SENDER = "notification@umitproject.org"
DEFAULT_NOTIFICATION_TO = "notification@umitproject.org"
DEFAULT_NOTIFICATION_REPLY_TO = "notification@umitproject.org"

#################
# MEDIA SETTINGS
MEDIA_DEV_MODE = DEBUG
DEV_MEDIA_URL = '/devmedia/'
PRODUCTION_MEDIA_URL = '/media/'

if PRODUCTION:
    MEDIA_URL = PRODUCTION_MEDIA_URL
    SITE_STATUS_DOMAIN = 'umit-site-status.appspot.com'
else:
    MEDIA_URL = DEV_MEDIA_URL
    SITE_STATUS_DOMAIN = 'apredoi-mac.eur.adobe.com:8000'


GLOBAL_MEDIA_DIRS = (os.path.join(os.path.dirname(__file__), 'media'),)

MEDIA_BUNDLES = (
    ('main.css',
     'css/reset.css',
     'css/style.css',
     'css/typography.css'
        ),
    ('main.js',
     'js/jquery.js',
     'js/main.js',
     'js/modernizr.js'
        ),
    )

ROOT_MEDIA_FILTERS = {
    'js': 'mediagenerator.filters.yuicompressor.YUICompressor',
    'css': 'mediagenerator.filters.yuicompressor.YUICompressor',
    }

YUICOMPRESSOR_PATH = os.path.join(os.path.dirname(__file__), 'yuicompressor-2.4.7.jar')


INTERNAL_IPS = ('127.0.0.1', 'localhost',)
LOGGING_OUTPUT_ENABLED = True


# add support to user profile
AUTH_PROFILE_MODULE = 'users.UserProfile'
ACCOUNT_ACTIVATION_DAYS = 30
LOGIN_REDIRECT_URL = '/'

EMAIL_BACKEND = 'appengineemail.EmailBackend'
#'django.core.mail.backends.console.EmailBackend'

if on_production_server:
    EMAIL_HOST = 'smtp.gmail.com'
    EMAIL_PORT = 587
    EMAIL_HOST_USER = 'gmailusername@gmail.com'
    EMAIL_HOST_PASSWORD = 'xxxxxxx'
    EMAIL_USE_TLS = True
    DEFAULT_FROM_EMAIL = 'gmailusername@gmail.com'
    SERVER_EMAIL = 'gmailusername@gmail.com'
else:
    # local
    EMAIL_HOST = 'localhost'
    EMAIL_PORT = 25

USE_I18N = True

SITENAME = "Site Status"

########################
# Registration settings
ACCOUNT_ACTIVATION_DAYS = 2

##################
# RESPONSE COUNTS
MAX_NETLIST_RESPONSE = 10
MAX_AGENTSLIST_RESPONSE = 5


