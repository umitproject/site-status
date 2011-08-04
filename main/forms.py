#!/usr/bin/env python

from django import forms


class SubscribeForm(forms.Form):
    email = forms.EmailField(required=True, label="E-mail")
    
class SubscribeOneTimeForm(SubscribeForm):
    one_time = forms.BooleanField(initial=False, required=False,
                                  label="I want to be notified only once, when system is available once again.",
                                  help_text="Leave this unchecked if you want to receive a notification whenever an incident occurs.")