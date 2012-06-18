from django.http import HttpResponse
from django.template.context import RequestContext
from django.shortcuts import render, render_to_response
from django.contrib.auth.models import User
from django.utils import simplejson
from django.utils.datastructures import MultiValueDictKeyError
from main.decorators import login_required
from main.backend.forms import ProfileForm, SiteConfigForm, ModuleForm
from main.models import SiteConfig, Module, UserProfile

__author__ = 'apredoi'


def backend(request):
    context = RequestContext(request)
    u = request.user

    profile_form = ProfileForm(initial={
        'username': u.username,
        'email': u.email,
        'first_name': u.first_name,
        'last_name': u.last_name,
        #'country': u.get_profile().country
    })


    site_config_form_template = SiteConfigForm()
    site_configs = SiteConfig.objects.filter(user=u)
    site_config_forms = []

    for site_config in site_configs:
        site_config_forms.append(SiteConfigForm(instance=site_config))

    module_form_template = ModuleForm()
    modules = Module.objects.filter(site_config__user=u)
    module_forms = []

    for module in modules:
        module_forms.append(ModuleForm(instance=module))


    return render(request, 'backend/home.html', {'profile_form':profile_form, 'site_config_forms': site_config_forms,
                                                 'site_config_form_template': site_config_form_template,
                                                 'module_forms' : module_forms,
                                                 'module_form_template' : module_form_template})


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
        return HttpResponse(simplejson.dumps({'error': 'inval form'}), mimetype='application/json' )
    return HttpResponse(simplejson.dumps({'status': 'ok'}), mimetype='application/json' )

@login_required
def add_site_config(request):
    if request.method == 'POST':
        object_key=None
        try:
            object_key = request.POST['site_config_id']
        except MultiValueDictKeyError:
            pass
        instance = None
        action = request.POST['site_config_action']
        if action in ('update', 'delete'):
            instance = SiteConfig.objects.get(user=request.user, pk=object_key)

        if instance and action == 'delete':
            instance.delete()
            return HttpResponse('{"action":"delete", "status":"ok", "id":"'+ object_key +'"}', mimetype='application/json')

        form = SiteConfigForm(request.POST,instance=instance) if instance else SiteConfigForm(request.POST)
        if form.is_valid():
            site_config = form.save(commit=False)
            site_config.user = request.user
            site_config.save()
        else:
            return HttpResponse(simplejson.dumps({'error': 'inval form'}), mimetype='application/json'
            )
        return HttpResponse('{"action":"' + action + '","status": "ok", "id":"'+ str(form.instance.pk) +'", '
                                '"item":"'+ form.as_table().replace('"','\\"').replace('\n','').replace('\r','') +'"}',
            mimetype='application/json')

    return HttpResponse('{"status": "ok"}', mimetype='application/json')


@login_required
def add_module(request):
    if request.method == 'POST':
        object_key=None
        try:
            object_key = request.POST['module_id']
        except MultiValueDictKeyError:
            pass
        instance = None
        action = request.POST['module_action']
        if action in ('update', 'delete'):
            instance = Module.objects.get(pk=object_key)

        if instance and action == 'delete':
            instance.delete()
            return HttpResponse('{"action":"delete", "status":"ok", "id":"'+ object_key +'"}', mimetype='application/json')

        form = ModuleForm(request.POST,instance=instance) if instance else ModuleForm(request.POST)
        if form.is_valid():
            module = form.save(commit=False)
            module.save()
        else:
            return HttpResponse(simplejson.dumps({'error': 'inval form'}), mimetype='application/json'
            )

        return HttpResponse('{"action":"' + action + '","status": "ok", "id":"'+ str(form.instance.pk) +'", '
                        '"item":"'+ form.as_table().replace('"','\\"').replace('\n','').replace('\r','') +'"}',
                        mimetype='application/json')

    return HttpResponse('{"status": "ok"}', mimetype='application/json')