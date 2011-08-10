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

from datetime import datetime

from django.conf import settings

EmailMessage = None
if settings.GAE:
    from google.appengine.api.mail import EmailMessage

def send_mail(sender, to, cc='', bcc='', reply_to='', subject='', body='', html='', attachments=[], headers={}):
    if settings.GAE:
        return _gae_send_mail(sender, to, cc, bcc, reply_to, subject, body, html, attachments, headers)

def _gae_send_mail(sender, to, cc=None, bcc=None, reply_to=None, subject='', body='', html='', attachments=[], headers={}):
    email = EmailMessage()
    email.sender = sender
    email.to = to
    email.subject = subject
    email.body = body
    if cc: email.cc = cc
    if bcc: email.bcc = bcc
    if reply_to: email.reply_to = reply_to
    if html: email.html = html
    if attachments: email.attachments = attachments
    if headers: email.headers = headers
    
    return email.send()

def pretty_date(time=False):
    """
    Copied from http://www.evaisse.net/2009/python-pretty-date-function-50002
    Code under the "Do What the Fuck you Want to Public License"
    
    Get a datetime object or a int() Epoch timestamp and return a
    pretty string like 'an hour ago', 'Yesterday', '3 months ago',
    'just now', etc
    """
    now = datetime.now()
    diff = None
    if type(time) is int:
        diff = now - datetime.fromtimestamp(time)
    elif not time:
        diff = now - now
    else:
        diff = now - time
    second_diff = diff.seconds
    day_diff = diff.days

    if day_diff < 0:
        return ''

    if day_diff == 0:
        if second_diff < 10:
            return "just now"
        if second_diff < 60:
            return str(second_diff) + " seconds ago"
        if second_diff < 120:
            return  "a minute ago"
        if second_diff < 3600:
            return str( second_diff / 60 ) + " minutes ago"
        if second_diff < 7200:
            return "an hour ago"
        if second_diff < 86400:
            return str( second_diff / 3600 ) + " hours ago"
    if day_diff == 1:
        return "Yesterday"
    if day_diff < 7:
        return str(day_diff) + " days ago"
    if day_diff < 31:
        return str(day_diff/7) + " weeks ago"
    if day_diff < 365:
        return str(day_diff/30) + " months ago"
    return str(day_diff/365) + " years ago"