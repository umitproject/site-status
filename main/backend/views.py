from django.http import HttpResponse
from django.template.context import RequestContext
from django.shortcuts import render, render_to_response
from django.contrib.auth.models import User
from django.utils import simplejson
from main.decorators import login_required
from main.backend.forms import ProfileForm

__author__ = 'apredoi'


@login_required
def backend(request):
    context = RequestContext(request)
    u = request.user
    form = ProfileForm(initial={
        'username': u.username,
        'email': u.email,
        'first_name': u.first_name,
        'last_name': u.last_name
    })
    return render(request, 'backend/home.html', {'form':form })


""" API """
@login_required
def update_profile(request):
    form = ProfileForm(request.POST)
    if form.is_valid():
        u = request.user
        if u.username != form.data.get('username'):
            return HttpResponse(simplejson.dumps({'error': 'invalid username'}), mimetype='application/json' )
        if form.data.get('first_name'):
            u.first_name = form.data.get('first_name')
        if form.data.get('last_name'):
            u.last_name = form.data.get('last_name')
        if form.data.get('password1'):
            u.set_password(form.data.get('password1'))
        u.save()
    else:
        return HttpResponse(simplejson.dumps({'error': 'inval form'}), mimetype='application/json' )

    return HttpResponse(simplejson.dumps({'status': 'ok'}), mimetype='application/json' )