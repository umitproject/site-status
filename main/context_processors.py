#!/usr/bin/env python
import logging

from django.conf import settings

from main.models import twitter_account

def get_settings(request):
    return {'GOOGLE_ANALYTICS_ID': settings.GOOGLE_ANALYTICS_ID,
            'SITE_NAME': settings.SITE_NAME,
            'MAIN_SITE_URL': settings.MAIN_SITE_URL,
            'CONTACT_PHONE': settings.CONTACT_PHONE,
            'CONTACT_EMAIL': settings.CONTACT_EMAIL,
            'twitter_account': twitter_account()}