#!/usr/bin/env python

import datetime

from django import template

from main.models import STATUS, Module

register = template.Library()

@register.simple_tag
def last_days_header(days):
    days = Module.show_days(int(days))
    header = []
    today = datetime.date.today()
    for day in xrange(days):
        header.append(today.strftime("<td>%x</td>"))
        today = today - datetime.timedelta(days=1)
    header.reverse()
    
    if len(header) > 0:
        header[-1] = "<td>Today</td>"
    else:
        header.append("<td>Today</td>")
    header.append("<td>Now</td>")
    return "\n".join(header)
last_days_header.is_safe = True

@register.simple_tag
def verbose_status(status):
    return dict(STATUS)[status]
verbose_status.is_safe = True