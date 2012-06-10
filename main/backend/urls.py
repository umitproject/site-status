from django.conf.urls.defaults import *
from django.contrib import admin

admin.autodiscover()

urlpatterns = patterns('',
    url('^$', 'main.backend.views.backend', name='backend'),
    url('^update_profile$', 'main.backend.views.update_profile', name='update_profile'),
)