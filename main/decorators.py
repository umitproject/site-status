# -*- coding: utf-8 -*-
from django.contrib.auth.decorators import login_required as django_login_required
from django.contrib.admin.views.decorators import staff_member_required as django_staff_member_required
from django.conf import settings

def login_required(view):
    if not settings.DEBUG:
        return django_login_required(view)
    return view

def staff_member_required(view):
    if not settings.DEBUG:
        def new_view(request, *args, **kwargs):
            # This is in order to bypass authentication if this header is present,
            # which indicates that appengine's cron is issuing this command
            if settings.GAE and request.META.get("X-AppEngine-Cron", False) == "true":
                return view(request, *args, **kwargs)
            return django_staff_member_required(view)(request, *args, **kwargs)
        return new_view
    return view
