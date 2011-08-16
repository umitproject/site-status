#!/usr/bin/env python
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

import datetime

from django import template

from main.models import STATUS, Module
from main.utils import pretty_date

register = template.Library()

@register.simple_tag(takes_context=True)
def last_days_header(context, days):
    days = Module.show_days(context['site_config'], int(days))
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

@register.simple_tag
def pretty_date(date):
    return pretty_date(date)
    