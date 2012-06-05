from django.template.context import RequestContext
from django.shortcuts import render
from main.decorators import login_required

__author__ = 'apredoi'


@login_required
def backend(request):
    context = RequestContext(request)
    return render(request, 'backend/home.html')