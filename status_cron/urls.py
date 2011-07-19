from django.conf.urls.defaults import *

urlpatterns = patterns('',
    url('^check_passive_hosts/?$', 'status_cron.views.check_passive_hosts', name='check_passive_hosts'),
)