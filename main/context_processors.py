#!/usr/bin/env python
from django.conf import settings

def get_settings(request):
    return {'settings': settings }