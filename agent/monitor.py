
import re
import time
import urllib2

import agent
from agent import settings

if settings.FREQUENCY < 1:
    FREQUENCY = 1

TEST_RE = re.compile('(.*)' if settings.TEST_URL_REGEX is None else settings.TEST_URL_REGEX)

def enter_mainloop():
    while True:
        # Run URL test
        response = urllib2.urlopen(settings.TEST_URL)
        
        # Check status code
        status_ok = response.status_code == 200
        
        # Run Regex against content
        status_ok = TEST_RE.match(response.read()) and status_ok
        
        # If something is wrong, send report if not disabled
        # If disabled, just print to output
        if not status_ok:
            if DISABLED:
                print "Failed to test module %s" % settings.MODULE_ID
            else:
                response = urllib2.urlopen(settings.API_URL + '/report_status', {'api_key': settings.API_KEY,
                                                                                 'api_secret': settings.API_KEY,
                                                                                 'module_id':settings.MODULE_ID})
        
        sleep(60 * FREQUENCY)

if __name__ == '__main__':
    enter_mainloop()