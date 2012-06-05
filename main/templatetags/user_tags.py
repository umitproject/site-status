from django import template
from django.contrib.auth.models import User

register = template.Library()

@register.simple_tag
def get_full_name(user):
    name = user.get_full_name()
    if not name :
        name = user.username
    return name


@register.simple_tag
def get_first_name(user):
    name = user.first_name
    if not name :
        name = user.username
    return name