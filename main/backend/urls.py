from django.conf.urls.defaults import *
from django.contrib import admin

admin.autodiscover()

urlpatterns = patterns('',
    url('^$', 'main.backend.views.backend', name='backend'),
    url('^update_profile$', 'main.backend.views.update_profile', name='update_profile'),
    url('^add_site_config', 'main.backend.views.add_site_config', name='add_site_config'),
    url('^add_module', 'main.backend.views.add_module', name='add_module'),
    url('^add_site_domain', 'main.backend.views.add_site_domain', name='add_site_domain'),
    url('^add_maintenance', 'main.backend.views.add_maintenance', name='add_maintenance'),
    url('^end_maintenance', 'main.backend.views.end_maintenance', name='end_maintenance'),
    url('^extend_maintenance', 'main.backend.views.extend_maintenance', name='extend_maintenance'),
)