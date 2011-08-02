from django.conf.urls.defaults import *
from django.contrib import admin

from main.feeds import LastModuleStatuses

admin.autodiscover()

handler500 = 'djangotoolbox.errorviews.server_error'

urlpatterns = patterns('',
    ('^_ah/warmup$', 'djangoappengine.views.warmup'),
    ('^$', 'main.views.home'),
    ('^subscribe/?$', 'main.views.subscribe'),
    ('^event/(?P<event_id>\d+)/?$', 'main.views.event'),
    
    ########
    # FEEDS
    (r'^feeds/(?P<module_id>\d+)/?$', LastModuleStatuses()),
    
    ########
    # TESTS
    ('^test_populate/?$', 'main.views.test_populate'),
    ('^test_events_and_aggregations/?$', 'main.views.test_events_and_aggregations'),
    
    ######
    # API
    (r'^api/', include('status_api.urls')),
    
    #######
    # Cron
    (r'^cron/', include('status_cron.urls')),
    
    ######################
    # Notification System
    (r'^notification/', include('status_notification.urls')),
    
    ########
    # ADMIN
    (r'^clean_cache/', 'main.views.clean_cache'),
    (r'^hard_reset/', 'main.views.hard_reset'),
    (r'^admin/', include(admin.site.urls)),
)
