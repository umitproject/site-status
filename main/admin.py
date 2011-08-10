from django.contrib import admin
from main.models import *

admin.site.register(Subscriber)
admin.site.register(NotifyOnEvent)
admin.site.register(Notification)
admin.site.register(AggregatedStatus)
admin.site.register(DailyModuleStatus)
admin.site.register(ModuleEvent)
admin.site.register(Module)
admin.site.register(ScheduledMaintenance)
admin.site.register(TwitterAccount)