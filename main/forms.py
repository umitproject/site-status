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


class SubscribeForm(forms.Form):
    email = forms.EmailField(required=True, label="E-mail")
    
class SubscribeOneTimeForm(SubscribeForm):
    one_time = forms.BooleanField(initial=False, required=False,
                                  label="I want to be notified only once, when system is available once again.",
                                  help_text="Leave this unchecked if you want to receive a notification whenever an incident occurs.")

class ScheduleMaintenanceForm(forms.Form):
    pass