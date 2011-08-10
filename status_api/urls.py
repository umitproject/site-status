from django.conf.urls.defaults import *

urlpatterns = patterns('',
    url('^report_status/?$', 'status_api.views.report_status', name='report_status'),
    url('^check_status/?$', 'status_api.views.check_status', name='check_status'),
    url('^check_incidents/?$', 'status_api.views.check_status', name='check_incidents'),
    url('^check_uptime/?$', 'status_api.views.check_status', name='check_uptime'),
    url('^check_availability/?$', 'status_api.views.check_status', name='check_availability'),
)