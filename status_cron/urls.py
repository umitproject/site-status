from django.conf.urls.defaults import *

urlpatterns = patterns('',
    url('^check_passive_hosts/?$', 'status_cron.views.check_passive_hosts', name='check_passive_hosts'),
    url('^check_passive_hosts_task/(?P<module_key>[0-9a-zA-Z\-\_]+)/?$', 'status_cron.views.check_passive_hosts_task', name='check_passive_hosts_task'),
    url('^aggregate_daily_status/?$', 'status_cron.views.aggregate_daily_status', name='aggregate_daily_status'),
    url('^check_notifications/?$', 'status_cron.views.check_notifications', name='check_notifications'),
    url('^send_notification_task/(?P<notification_id>[0-9a-zA-Z\-\_]+)/?$', 'status_cron.views.send_notification_task', name='send_notification_task'),
)