#!/usr/bin/env python
import os
import sys

sys.stdout = sys.stderr

os.environ['SERVER_SOFTWARE'] = 'Development'
os.environ['DJANGO_SETTINGS_MODULE'] = 'settings'

from django.core.management import execute_manager
from django.conf import settings

import settings

if __name__ == "__main__":
    execute_manager(settings)
