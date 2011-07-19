from django.conf.urls.defaults import *

urlpatterns = patterns('',
    url('^check_passive_hosts/?$', 'status_cron.views.check_passive_hosts', name='check_passive_hosts'),
    url('^check_passive_hosts_task/(?P<module_key>[0-9a-zA-Z\-\_]+)/?$', 'status_cron.views.check_passive_hosts_task', name='check_passive_hosts_task'),
)