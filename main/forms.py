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

from django import forms
from django.utils.translation import ugettext_noop as _
from django.forms.formsets import formset_factory
from main.models import Subscriber

class SubscribeForm(forms.Form):
    email = forms.EmailField(required=True, label=_("E-mail"))
    
class SubscribeOneTimeForm(SubscribeForm):
    one_time = forms.BooleanField(initial=False, required=False,
                                  label=_("I want to be notified only once, when system is available once again."),
                                  help_text=_("Leave this unchecked if you want to receive a notification whenever an incident occurs."))

class UnsubscribeForm(forms.Form):
    uuid = forms.CharField(label="",widget=forms.HiddenInput(),required=False)
    subscription_id = forms.IntegerField(label="",widget=forms.HiddenInput(),required=False)

UnsubscribeFormFactory = formset_factory(UnsubscribeForm,extra=0)

class UnsubscribeAllForm(forms.Form):
    uuid = forms.CharField(label="",widget=forms.HiddenInput())

class SubscriberSettings(forms.ModelForm):
    unique_identifier = forms.CharField(label="",widget=forms.HiddenInput())

    def __init__(self, *args, **kw):
        super(forms.ModelForm, self).__init__(*args, **kw)
        self.fields.keyOrder = ['debounce_timer','unique_identifier']
    class Meta:
        model=Subscriber
