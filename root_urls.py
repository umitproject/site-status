__author__ = 'apredoi'
from django.conf.urls.defaults import *
from django.contrib import admin

from main.feeds import LastModuleStatuses

admin.autodiscover()

handler500 = 'djangotoolbox.errorviews.server_error'

urlpatterns = patterns('',
    url('^$', 'main.views.root_home', name='root_home')
)