#!/usr/bin/env python

import datetime

from django.shortcuts import render_to_response
from django.http import HttpResponse, Http404
from django.conf import settings

from main.models import *


def home(request):
    
    context = locals()
    return render_to_response('home.html', context)

def subscribe(request):
    
    context = locals()
    return render_to_response('subscribe.html', context)

def test_populate(request):
    if settings.DEBUG:
        if not Module.objects.filter(name="Umit Project"):
            umit = Module()
            umit.name = "Umit Project"
            umit.description = "This is our main website."
            umit.module_type = "passive"
            umit.host = "www.umitproject.org"
            umit.url = "http://www.umitproject.org"
            umit.save()
        
        if not Module.objects.filter(name="Trac"):
            trac = Module()
            trac.name = "Trac"
            trac.description = "This is our old development site, based on Trac."
            trac.module_type = "passive"
            trac.host = "trac.umitproject.org"
            trac.url = "http://trac.umitproject.org"
            trac.save()
        
        if not Module.objects.filter(name="Redmine"):
            redmine = Module()
            redmine.name = "Redmine"
            redmine.description = "This is our new development site, based on Redmine."
            redmine.module_type = "passive"
            redmine.host = "dev.umitproject.org"
            redmine.url = "http://dev.umitproject.org"
            redmine.save()
        
        if not Module.objects.filter(name="Git"):
            git = Module()
            git.name = "Git"
            git.description = "This is our git repository."
            git.module_type = "passive"
            git.host = "git.umitproject.org"
            git.url = "http://git.umitproject.org"
            git.save()
        
        if not Module.objects.filter(name="Blog"):
            blog = Module()
            blog.name = "Blog"
            blog.description = "This is organizational blog."
            blog.module_type = "passive"
            blog.host = "blog.umitproject.org"
            blog.url = "http://blog.umitproject.org"
            blog.save()
        
        context = locals()
        context['msg'] = 'Test Populate OK'
        return render_to_response('home.html', context)
    
    raise Http404