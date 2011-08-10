
from django.http import Http404

from main.models import Module

def authenticate_api_request(view):
    def new_view(request, *args, **kwargs):
        api = request.POST['module_api']
        secret = request.POST['module_secret']
        module = request.POST['module']
        
        module = Module.objects.filter(pk=module)
        if module:
            module = module[0]
            if module.authenticate(api, secret):
                request.module = module
                return view(request, *args, **kwargs)
        
        raise Http404
    return new_view