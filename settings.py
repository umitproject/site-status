# Initialize App Engine and import the default settings (DB backend, etc.).
# If you want to use a different backend you have to remove all occurences
# of "djangoappengine" from this file.
from djangoappengine.settings_base import *

import os

# Activate django-dbindexer for the default database
DATABASES['native'] = DATABASES['default']
DATABASES['default'] = {'ENGINE': 'dbindexer', 'TARGET': 'native'}
AUTOLOAD_SITECONF = 'indexes'

DEBUG = True
SITE_NAME = "Umit Project"
MAIN_SITE_URL = "http://www.umitproject.org"
CONTACT_PHONE = "+55 62 6262626262"
CONTACT_EMAIL = "contact@umitproject.org"

GOOGLE_ANALYTICS_ID = ''

ENVIRONMENT = os.environ.get('SERVER_SOFTWARE', '')
GAE = True
PRODUCTION = True
TEST = False

if ENVIRONMENT == '':
    # TODO: Figure how to check if running on prod in other environments
    GAE = False
elif ENVIRONMENT.startswith('Development'):
    PRODUCTION = False
elif ENVIRONMENT.startswith('GAETest'):
    TEST = True


#####################
# CURRENT STATUS BAR
SHOW_INCIDENTS = True
SHOW_UPTIME = True
SHOW_LAST_INCIDENT = True

######################
# NOTIFICATION SYSTEM

NOTIFICATION_SYSTEM = 'courrier' # One of courrier or e-mail

COURRIER_CUSTOMER_KEY = ''
COURRIER_API_SECRET = ''
COURRIER_STATUS_CAMPAIGN_KEY = ""

#EMAIL_HOST = ''
#EMAIL_HOST_USER = ''
#EMAIL_HOST_PASSWORD = ''
#EMAIL_PORT = 25
#EMAIL_USE_TLS = False


########################
# MEDIA HANDLING SECTION

MEDIA_DEV_MODE = DEBUG
DEV_MEDIA_URL = '/devmedia/'
PRODUCTION_MEDIA_URL = '/media/'

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
    ),
)

ROOT_MEDIA_FILTERS = {
    'js': 'mediagenerator.filters.yuicompressor.YUICompressor',
    'css': 'mediagenerator.filters.yuicompressor.YUICompressor',
}

YUICOMPRESSOR_PATH = os.path.join(os.path.dirname(__file__),
                                  'yuicompressor-2.4.6.jar')

#########################

SECRET_KEY = '=r-$b*8hglm+858&9t043hlm6-&6-3d3vfc4((7yd0dbrakhvi'

INSTALLED_APPS = (
    'django.contrib.admin',
    'django.contrib.contenttypes',
    'django.contrib.messages',
    'django.contrib.auth',
    'django.contrib.sessions',
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

ROOT_URLCONF = 'urls'
