from django.conf.urls.defaults import *
from django.contrib import admin

admin.autodiscover()

handler500 = 'djangotoolbox.errorviews.server_error'

urlpatterns = patterns('',
    ('^_ah/warmup$', 'djangoappengine.views.warmup'),
    ('^$', 'main.views.home'),
    ('^subscribe/?$', 'main.views.subscribe'),
    ('^test_populate/?$', 'main.views.test_populate'),
    
    #######
    # ADMIN
    (r'^admin/', include(admin.site.urls)),
)
