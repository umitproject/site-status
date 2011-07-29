from django.conf.urls.defaults import *
from django.contrib import admin

admin.autodiscover()

handler500 = 'djangotoolbox.errorviews.server_error'

urlpatterns = patterns('',
    ('^_ah/warmup$', 'djangoappengine.views.warmup'),
    ('^$', 'main.views.home'),
    ('^subscribe/?$', 'main.views.subscribe'),
    
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
