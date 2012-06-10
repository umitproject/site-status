from django.http import HttpResponse
from django.template.context import RequestContext
from django.shortcuts import render, render_to_response
from django.contrib.auth.models import User
from django.utils import simplejson
from main.decorators import login_required
from main.backend.forms import ProfileForm
from main.models import UserProfile

__author__ = 'apredoi'


@login_required
def backend(request):
    context = RequestContext(request)
    u = request.user
    form = ProfileForm(initial={
        'username': u.username,
        'email': u.email,
        'first_name': u.first_name,
        'last_name': u.last_name,
        'country': u.get_profile().country
    })
    return render(request, 'backend/home.html', {'form':form })


""" API """
@login_required
def update_profile(request):
    form = ProfileForm(request.POST)
    if form.is_valid():

        u = request.user
        u_profile = UserProfile.objects.get_or_create(user = request.user)[0]
        if u.username != form.data.get('username'):
            return HttpResponse(simplejson.dumps({'error': 'invalid username'}), mimetype='application/json' )
        if form.data.get('first_name'):
            u.first_name = form.data.get('first_name')
        if form.data.get('last_name'):
            u.last_name = form.data.get('last_name')
        if form.data.get('birth_date'):
            u_profile.birth_date = form.data.get('birth_date')
        if form.data.get('address'):
            u_profile.address = form.data.get('address')
        if form.data.get('city'):
            u_profile.city = form.data.get('city')
        if form.data.get('country'):
            u_profile.country = form.data.get('country')
        if form.data.get('state'):
            u_profile.state = form.data.get('state')
        if form.data.get('phone_number'):
            u_profile.phone_number = form.data.get('phone_number')
        if form.data.get('password1'):
            u.set_password(form.data.get('password1'))
        u_profile.save()
        u.save()

    else:

        return HttpResponse(simplejson.dumps({'error': 'validation', 'message': form.errors}), mimetype='application/json' )

    return HttpResponse(simplejson.dumps({'status': 'ok'}), mimetype='application/json' )