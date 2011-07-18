from django.conf.urls.defaults import *

urlpatterns = patterns('',
    url('^save_active_host_status/?$', 'status_api.views.save_active_host_status', name='save_active_host_status'),
)