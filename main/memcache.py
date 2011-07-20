#!/usr/bin/env python

from django.conf import settings

memcache = None

if settings.GAE:
    from google.appengine.api import memcache