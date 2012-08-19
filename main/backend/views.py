from datetime import datetime
import base64
import cStringIO
from django.core.urlresolvers import reverse
from django.template.loader import render_to_string
from django.http import HttpResponse, Http404
from django.template.context import RequestContext
from django.shortcuts import render, render_to_response, get_object_or_404, redirect
from django.contrib.auth.models import User
from django.utils import simplejson
from django.utils.datastructures import MultiValueDictKeyError
from django.core.cache import cache
import re
from urlparse import urlparse
from django.views.decorators.csrf import csrf_protect
from main.decorators import login_required
from main.backend.forms import ProfileForm, SiteConfigForm, ModuleForm, StatusSiteDomainForm, ScheduledMaintenanceForm, ScheduledMaintenanceTemplateForm, StatusSiteCustomizationForm
from main.middleware import DOMAIN_SITE_CONFIG_CACHE_KEY

from main.models import SiteConfig, Module, UserProfile, StatusSiteDomain, STATUS, ScheduledMaintenance, Notification

__author__ = 'apredoi'

@login_required
def backend(request):
    context = RequestContext(request)
    u = request.user
    u_profile = UserProfile.objects.get_or_create(user = request.user)[0]

    initial_data = u.__dict__
    initial_data.update(u_profile.__dict__)

    profile_form = ProfileForm(initial=initial_data)


    site_config_form_template = SiteConfigForm()
    site_configs = SiteConfig.objects.filter(user=u)
    site_config_forms = []

    for site_config in site_configs:
        site_config_forms.append(SiteConfigForm(instance=site_config))

    module_form_template = ModuleForm(u)
    modules = Module.objects.filter(site_config__user=u)
    module_forms = []

    for module in modules:
        module_forms.append(ModuleForm(u,instance=module))

    maintenance_form_template = ScheduledMaintenanceTemplateForm(u)
    maintenances = ScheduledMaintenance.objects.filter(site_config__user=u)

    site_domain_form_template = StatusSiteDomainForm(u)
    site_domains = StatusSiteDomain.objects.filter(site_config__user=u)
    site_domain_forms = []

    for site_domain in site_domains:
        site_domain_forms.append(StatusSiteDomainForm(u,instance=site_domain))

    return render(request, 'backend/home.html', {'profile_form':profile_form,
                                                 'site_config_forms': site_config_forms,
                                                 'site_config_form_template': site_config_form_template,
                                                 'module_forms' : module_forms,
                                                 'module_form_template' : module_form_template,
                                                 'site_domain_forms' : site_domain_forms,
                                                 'site_domain_form_template' : site_domain_form_template,
                                                 'maintenance_form_template' : maintenance_form_template,
                                                 'maintenances' : maintenances
                                                 })


""" API """
@login_required
def update_profile(request):
    form = ProfileForm(request.POST)
    response_obj = {'status': 'ok', 'target': 'profile'}

    if form.is_valid():
        u = request.user
        u_profile = UserProfile.objects.get_or_create(user = request.user)[0]
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
        response_obj['error'] = form.errors
        response_obj['status'] = 'error'
        return HttpResponse(simplejson.dumps(response_obj), mimetype='application/json' )
    return HttpResponse(simplejson.dumps(response_obj), mimetype='application/json' )

@login_required
def add_site_config(request):
    response_obj = {'status': 'ok', 'target': 'site_config'}
    if request.method == 'POST':
        object_key=None
        try:
            object_key = request.POST['site_config_id']
        except MultiValueDictKeyError:
            response_obj['action'] = 'add'
        instance = None
        action = request.POST['site_config_action']
        if action in ('update', 'delete') and object_key is not None:
            instance = SiteConfig.get_from_id(object_key)
            if instance.user != request.user:
                raise Http404
            response_obj['id'] = object_key
            response_obj['action'] = 'update'

        if instance and action == 'delete':
            instance.delete()
            response_obj['action'] = 'delete'
            return HttpResponse(simplejson.dumps(response_obj), mimetype='application/json')

        form = SiteConfigForm(request.POST,instance=instance) if instance else SiteConfigForm(request.POST)
        if form.is_valid():
            site_config = form.save(commit=False)
            site_config.user = request.user
            site_config.save()
            response_obj['id'] = site_config.pk
        else:
            response_obj['error'] = form.errors
            response_obj['status'] = 'error'
            response_obj['item'] = render_to_string("backend/site_config_form.html", dict(site_config_form=form))
            return HttpResponse(simplejson.dumps(response_obj), mimetype='application/json'
            )
        response_obj['item'] = render_to_string("backend/site_config_form.html",
                                                            dict(site_config_form=SiteConfigForm(instance=site_config)))
        response_obj['name'] = site_config.site_name
        return HttpResponse(simplejson.dumps(response_obj), mimetype='application/json')

    return HttpResponse(response_obj, mimetype='application/json')


@login_required
def add_module(request):
    response_obj = {'status': 'ok', 'target': 'module'}
    if request.method == 'POST':
        object_key=None

        try:
            object_key = request.POST['module_id']
        except MultiValueDictKeyError:
            response_obj['action'] = 'add'
        instance = None
        action = request.POST['module_action']

        if action in ('update', 'delete') and object_key is not None:
            instance = Module.objects.get(pk=object_key)
            response_obj['id'] = object_key
            response_obj['action'] = 'update'

        if instance and action == 'delete':
            instance.delete()
            response_obj['action'] = 'delete'
            return HttpResponse(simplejson.dumps(response_obj), mimetype='application/json')

        form = ModuleForm(request.user,request.POST,instance=instance) if instance else ModuleForm(request.user,request.POST)
        if form.is_valid():
            module = form.save(commit=False)
            module.updated_at = datetime.now()
            #add
            if not instance:
                module.monitoring_since = datetime.now()
                module.status = "unknown"
                module.total_downtime = "0.0"

            module.save()
            instance = module
            response_obj['id'] = module.pk
        else:
            response_obj['status'] = 'error'
            response_obj['error'] = form.errors
            return HttpResponse(simplejson.dumps(response_obj), mimetype='application/json'
            )
        response_obj['item'] = render_to_string("backend/module_form.html",
                                    dict(module_form=ModuleForm(request.user,instance=instance)))
        response_obj['name'] = module.name
        return HttpResponse(simplejson.dumps(response_obj), mimetype='application/json')

    return HttpResponse(simplejson.dumps(response_obj), mimetype='application/json')

@login_required
def add_site_domain(request):
    response_obj = {'status': 'ok', 'target': 'site_domain'}
    if request.method == 'POST':
        object_key=None

        try:
            object_key = request.POST['site_domain_id']
        except MultiValueDictKeyError:
            response_obj['action'] = 'add'

        instance = None
        action = request.POST['site_domain_action']
        if action in ('update', 'delete'):
            instance = StatusSiteDomain.objects.get(pk=object_key)
            response_obj['id'] = object_key
            response_obj['action'] = 'update'

        if instance and action == 'delete':
            response_obj['action'] = 'delete'
            try:
                instance.delete()
            except Exception,e:
                response_obj['status'] = "error"
            return HttpResponse(simplejson.dumps(response_obj), mimetype='application/json')

        form = StatusSiteDomainForm(request.user,request.POST,instance=instance) if instance else StatusSiteDomainForm(request.user,request.POST)
        if form.is_valid():
            site_domain = form.save(commit=False)
            if site_domain.status_url.startswith('http://') or site_domain.status_url.startswith('https://'):
                site_domain.status_url = urlparse(site_domain.status_url).hostname
            site_domain.save()
            response_obj['id'] = site_domain.pk
        else:
            response_obj['status'] = 'error'
            response_obj['error'] = form.errors
            return HttpResponse(simplejson.dumps(response_obj), mimetype='application/json'
            )

        response_obj['name'] = site_domain.status_url
        response_obj['item'] = render_to_string("backend/site_domain_form.html", dict(site_domain_form=form))
        return HttpResponse(simplejson.dumps(response_obj), mimetype='application/json')

    return HttpResponse(simplejson.dumps(response_obj), mimetype='application/json')


@login_required
def toggle_site_config_url(request):
    response_obj = {'status': 'ok', 'target': 'site_domain', 'action':'toggle'}
    if request.method == 'POST':
        url = request.POST.get('url',False)
        if url:
            if url.startswith("/sites/"):
                site_config_id = re.findall(r'\d+', url)[0]
                site_config = SiteConfig.get_from_id(site_config_id)
                if site_config:
                    site_config.public_internal_url = not site_config.public_internal_url
                    site_config.save()
            else:
                parse_result = urlparse(url)
                host = parse_result.hostname
                if parse_result.port:
                    host += ":"+str(parse_result.port)
                site_config_domain = StatusSiteDomain.objects.get(status_url=host)
                if site_config_domain:
                    site_config_domain.public = not site_config_domain.public
                    site_config_domain.save()

    return HttpResponse(simplejson.dumps(response_obj), mimetype='application/json')


@login_required
def toggle_public_module(request):
    response_obj = {'status': 'ok', 'target': 'module', 'action':'toggle'}
    if request.method == 'POST':
        module_id = request.POST.get('module_id',False)
        module = Module.objects.filter(id=module_id)
        if module:
            module = module[0]
            module.public = not module.public
            module.save()

    return HttpResponse(simplejson.dumps(response_obj), mimetype='application/json')

@login_required
def add_maintenance(request):
    response_obj = {'status': 'ok', 'target': 'maintenance'}

    if request.method == 'POST':
        object_key=None

        try:
            object_key = request.POST['maintenance_id']
        except MultiValueDictKeyError:
            response_obj['action'] = 'add'

        instance = None
        action = request.POST['maintenance_action']
        if action in ('update', 'delete'):
            instance = ScheduledMaintenance.objects.get(pk=object_key)
            response_obj['id'] = object_key
            response_obj['action'] = 'update'

        if instance and action == 'delete':
            response_obj['action'] = 'delete'
            try:
                instance.delete()
            except Exception,e:
                response_obj['status'] = "error"
            return HttpResponse(simplejson.dumps(response_obj), mimetype='application/json')

        form = ScheduledMaintenanceForm(request.user,request.POST,instance=instance) if instance else ScheduledMaintenanceForm(request.user,request.POST)
        if form.is_valid():
            maintenance = form.save(commit=False)
            #add
            if not instance:
                maintenance.created_at = datetime.now()
                maintenance.status = "unknown"
                maintenance.total_downtime = 0.0
                maintenance.module = Module.objects.get(pk=request.POST['module_id'])
                maintenance.site_config = SiteConfig.get_from_id(request.POST.get('site_config_id',None))

            maintenance.updated_at = datetime.now()
            maintenance.save()
            response_obj['id'] = maintenance.pk
        else:
            response_obj['status'] = 'error'
            response_obj['error'] = form.errors
            return HttpResponse(simplejson.dumps(response_obj), mimetype='application/json'
            )

        response_obj['name'] = 'maintenance'
        response_obj['item'] = maintenance.pk
        return HttpResponse(simplejson.dumps(response_obj), mimetype='application/json')

    return HttpResponse(simplejson.dumps(response_obj), mimetype='application/json')


@login_required
def end_maintenance(request):
    response_obj = {'status': 'ok', 'target': 'maintenance'}

    if request.method == 'POST':
        object_key = request.POST.get("maintenance_id")
        if object_key:
            maintenance = ScheduledMaintenance.objects.get(id=object_key,site_config__user=request.user)
            if maintenance:
                if maintenance.is_undergoing:
                    maintenance.time_estimate = (datetime.now() - maintenance.scheduled_to).total_seconds() / 60
                    maintenance.save()
                elif maintenance.is_in_the_future:
                    maintenance.delete()
    return HttpResponse(simplejson.dumps(response_obj), mimetype='application/json')


@login_required
def extend_maintenance(request):
    response_obj = {'status': 'ok', 'target': 'maintenance'}

    if request.method == 'POST':
        object_key = request.POST.get("maintenance_id")
        value = request.POST.get("extend_value", 10)
        if object_key:
            maintenance = ScheduledMaintenance.objects.get(id=object_key,site_config__user=request.user)
            if maintenance:
                maintenance.time_estimate += int(value) * 60 # seconds
                maintenance.save()

    return HttpResponse(simplejson.dumps(response_obj), mimetype='application/json')


@login_required
def reset_api(request):
    response_obj = {'status': 'ok', 'target': 'reset_api'}

    if request.method == 'POST' :
        object_key = request.POST['site_config_id']
        instance = SiteConfig.get_from_id(object_key)
        if instance and instance.user == request.user:
            instance.api_key = None
            instance.api_secret = None
            instance.save()

    return HttpResponse(simplejson.dumps(response_obj), mimetype='application/json')


def _handle_uploaded_file(f):
    output = cStringIO.StringIO()
    base64.encode(f, output)
    return "data:" + f.content_type + ";base64," + output.getvalue()


@login_required
def customize_site_status(request, site_id):
    if request.method == 'POST':
        customization_form = StatusSiteCustomizationForm(request.POST, request.FILES)
        if customization_form.is_valid():
            action = request.POST.get('customization-action', "save")
            id = customization_form.cleaned_data.get('site_config_id')
            site_config = get_object_or_404(SiteConfig, id=id, user=request.user)

            if action == 'save':
                logo_file = request.FILES.get('logo', False)
                if logo_file:
                    site_config.logo = _handle_uploaded_file(logo_file)
                site_config.custom_css = customization_form.cleaned_data.get('custom_css')

                site_config.preview_custom_css = None
                site_config.preview_logo = None

                site_config.save()
            elif action == 'preview':
                logo_file = request.FILES.get('logo', False)
                if logo_file:
                    site_config.preview_logo = _handle_uploaded_file(logo_file)

                site_config.preview_custom_css = customization_form.cleaned_data.get('custom_css')
                site_config.save()
                return redirect( reverse("home", kwargs={'site_id':site_config.id}) + '?preview=true')

            elif action == 'remove_logo':
                site_config.logo = None
                site_config.save()
        else:
            site_config = get_object_or_404(SiteConfig, id=site_id, user=request.user)
    elif request.method == 'GET':
        site_config = get_object_or_404(SiteConfig, id=site_id, user=request.user)
        customization_form = StatusSiteCustomizationForm(initial=dict({'site_config_id': site_id, 'custom_css': site_config.preview_custom_css or site_config.custom_css}))

    context = RequestContext(request,locals())

    return render_to_response('backend/customize_site_status.html',context)


@login_required
def notification_site_status (request, site_id):
    if request.method == 'POST':
        action = request.POST.get('notification-action', "send")
        notification_id = request.POST.get('notification_id', None)
        notification = get_object_or_404(Notification, id=notification_id)
        if action == 'send':
            notification.send = True
            notification.save()
        elif action == 'delete':
            notification.delete()

    notifications = Notification.objects.filter(site_config__id=site_id)
    context = RequestContext(request, locals())

    return render_to_response('backend/notification_site_status.html',context)