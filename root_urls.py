import urls

__author__ = 'apredoi'
from django.conf.urls.defaults import *
from django.contrib import admin
from registration import *
import django_cron

django_cron.autodiscover()

from main.feeds import LastModuleStatuses

admin.autodiscover()

handler500 = 'djangotoolbox.errorviews.server_error'

urlpatterns = patterns('',
    url('^$', 'main.views.root_home', name='root_home'),
    url(r'^accounts/', include('registration.backends.default.urls')),
    url(r'^backend/', include('main.backend.urls')),

    ########
    # TESTS
    url('^test_populate/?$', 'main.views.test_populate', name='test_populate'),
    url('^test_events_and_aggregations/?$', 'main.views.test_events_and_aggregations', name='test_events_and_aggregations'),
    url(r'^hard_reset/', 'main.views.hard_reset', name='hard_reset'),


    #LOG OUTPUT
    url('^log/(?P<log_name>monitor(\d+)\.log(\.(\d+-\d+-\d+))?)/?$', 'main.views.log', name='module_log_viewer'),


    ########
    # FEEDS
    url(r'^feeds/(?P<module_id>\d+)/?$', LastModuleStatuses(), name='feeds'),

    ######
    # API
    # TODO: ADD THESE BACK
    url(r'^api/', include('status_api.urls')),

    #######
    # Cron
    # TODO: ADD THESE BACK
    url(r'^cron/', include('status_cron.urls')),

    ######################
    # Notification System
    url(r'^notification/', include('status_notification.urls')),

    ########
    # ADMIN
    url(r'^clean_cache/', 'main.views.clean_cache', name='clean_cache'),
    url(r'^admin/', include(admin.site.urls)),
    url(r'^accounts/login/$', 'django.contrib.auth.views.login', name='login'),

    #######
    # site_config
    url(r'^sites/(?P<site_slug>[a-z0-9\-_]+)/', include('urls')),


    url('^sites/(?P<site_slug>[a-z0-9\-_]+)/unsubscribe/?$', 'main.views.unsubscribe', name='private_unsubscribe'),
)