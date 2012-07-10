#!/usr/bin/env python
# -*- coding: utf-8 -*-
##
## Author: Adriano Monteiro Marques <adriano@umitproject.org>
##
## Copyright (C) 2011 S2S Network Consultoria e Tecnologia da Informacao LTDA
##
## This program is free software: you can redistribute it and/or modify
## it under the terms of the GNU Affero General Public License as
## published by the Free Software Foundation, either version 3 of the
## License, or (at your option) any later version.
##
## This program is distributed in the hope that it will be useful,
## but WITHOUT ANY WARRANTY; without even the implied warranty of
## MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
## GNU Affero General Public License for more details.
##
## You should have received a copy of the GNU Affero General Public License
## along with this program.  If not, see <http://www.gnu.org/licenses/>.
##

import re
from time import sleep
import urllib2

import logging

import agent
from agent import settings
from agent.settings import DISABLED

FREQUENCY = settings.FREQUENCY
if FREQUENCY < 1:
    FREQUENCY = 1

TEST_RE = re.compile('(.*)' if settings.TEST_URL_REGEX is None else settings.TEST_URL_REGEX)

def enter_mainloop():
    current_status = agent.call('check_status').get('status', 'unknown')

    while True:
        # Run URL test
        if not agent.test_url(settings.TEST_URL, TEST_RE):
            if settings.DISABLED:
                logging.warning("Failed to test module %s" % settings.MODULE_ID)
            else:
                response = agent.call('report_status', module_status='off-line')
                logging.warning('Status reported: %s' % response)
            current_status = 'off-line'
        else:
            if current_status != 'on-line' and not DISABLED:
                response = agent.call('report_status', module_status='on-line')
                logging.warning('Status reported: %s' % response)
                current_status = 'on-line'
            
            logging.warning('Succeed!')
        
        sleep(60 * FREQUENCY)

if __name__ == '__main__':
    enter_mainloop()