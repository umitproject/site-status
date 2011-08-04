from django.conf.urls.defaults import *
from django.contrib import admin

from main.feeds import LastModuleStatuses

admin.autodiscover()

handler500 = 'djangotoolbox.errorviews.server_error'

urlpatterns = patterns('',
    url('^_ah/warmup$', 'djangoappengine.views.warmup'),
    url('^$', 'main.views.home', name='home'),
    url('^subscribe/event/(?P<event_id>\d+)/?$', 'main.views.subscribe', name='event_subscribe'),
    url('^subscribe/module/(?P<module_id>\d+)/?$', 'main.views.subscribe', name='module_subscribe'),
    url('^subscribe/?$', 'main.views.subscribe', name='system_subscribe'),
    url('^event/(?P<event_id>\d+)/?$', 'main.views.event', name='event'),
    
    ########
    # FEEDS
    url(r'^feeds/(?P<module_id>\d+)/?$', LastModuleStatuses(), name='feeds'),
    
    ########
    # TESTS
    url('^test_populate/?$', 'main.views.test_populate', name='test_populate'),
    url('^test_events_and_aggregations/?$', 'main.views.test_events_and_aggregations', name='test_events_and_aggregations'),
    
    ######
    # API
    url(r'^api/', include('status_api.urls')),
    
    #######
    # Cron
    url(r'^cron/', include('status_cron.urls')),
    
    ######################
    # Notification System
    url(r'^notification/', include('status_notification.urls')),
    
    ########
    # ADMIN
    url(r'^clean_cache/', 'main.views.clean_cache', name='clean_cache'),
    url(r'^hard_reset/', 'main.views.hard_reset', name='hard_reset'),
    url(r'^admin/', include(admin.site.urls)),
)
