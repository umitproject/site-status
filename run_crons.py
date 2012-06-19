#! /usr/bin/env python

import sys
import os

def setup_environment():
    pathname = os.path.dirname(__file__)
    sys.path.append(os.path.abspath(pathname))
    sys.path.append(os.path.normpath(os.path.join(os.path.abspath(pathname), '../')))
    sys.path.append(os.path.normpath(os.path.join(os.path.abspath(pathname), 'lib/')))
    os.environ['DJANGO_SETTINGS_MODULE'] = 'settings'

# Must set up environment before imports.
setup_environment()

from django_cron import cronScheduler

def main(argv=None):
    cronScheduler.run_jobs()

if __name__ == '__main__':
    main()