from django.conf.urls.defaults import *
from django.contrib import admin

admin.autodiscover()

urlpatterns = patterns('',
    url('^$', 'main.backend.views.backend', name='backend'),
    url('^update_profile$', 'main.backend.views.update_profile', name='update_profile'),
    url('^add_site_config', 'main.backend.views.add_site_config', name='add_site_config'),
    url('^add_module', 'main.backend.views.add_module', name='add_module'),
)