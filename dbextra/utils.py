__author__ = 'apredoi'

import logging
import fields
from main.models import Module

MAX_LOG_ENTRIES = 3000

# Create your models here.
class ModuleListFieldHandler(logging.Handler): # Inherit from logging.Handler
    def __init__(self, module_id):
        # run the regular Handler __init__
        logging.Handler.__init__(self)
        # Our custom argument
        self.module = Module.objects.get(pk=module_id)
    def emit(self, record):
        # record.message is the log message
        if self.module:
            self.module.logs.append(record.getMessage())
            #rotate
            self.module.logs = self.module.logs[-MAX_LOG_ENTRIES:]
            self.module.save()