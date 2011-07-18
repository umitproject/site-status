#!/usr/bin/env python

import datetime

from django import template

register = template.Library()

@register.simple_tag
def last_days_header(days):
    days = int(days)
    header = []
    today = datetime.date.today()
    for day in xrange(days):
        header.append(today.strftime("<td>%x</td>"))
        today = today - datetime.timedelta(days=1)
    header.reverse()
    header[-1] = "<td>Today</td>"
    header.append("<td>Now</td>")
    return "\n".join(header)
last_days_header.is_safe = True 