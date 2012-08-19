import datetime
from django import forms
from django.contrib.admin import widgets
from django.core import validators
from django.contrib.auth.models import User
from django.utils.translation import ugettext_lazy as _
from main.models import SiteConfig, UserProfile, Module, StatusSiteDomain, PORT_CHECK_OPTIONS, ScheduledMaintenance


class ProfileForm(forms.ModelForm):
    class Meta:
        model=UserProfile
        exclude=('user', 'username', 'email')

    first_name = forms.CharField(max_length=30, required=False)
    last_name = forms.CharField(max_length=30, required=False)
    password1 = forms.CharField(widget=forms.PasswordInput(render_value=False),
        label=_("Password"),
        validators=[validators.MinLengthValidator(4)],
        error_messages={'min_length': _('Password must be at least 4 characters')},
        required = False)
    password2 = forms.CharField(widget=forms.PasswordInput(render_value=False),
        label=_("Password (again)"), required=False)

    def __init__(self, *args, **kw):
        super(forms.ModelForm, self).__init__(*args, **kw)
        self.fields.keyOrder = ['first_name', 'last_name','birth_date', 'address', 'city', 'country',
                           'state', 'phone_number','password1', 'password2']

    def clean(self):
        cleaned_data = super(ProfileForm, self).clean()
        if 'password1' in cleaned_data and 'password2' in cleaned_data:
            if cleaned_data['password1'] != cleaned_data['password2']:
                raise forms.ValidationError(_("The two password fields didn't match."))
        return self.cleaned_data


class SiteConfigForm(forms.ModelForm):
    class Meta:
        model = SiteConfig
        exclude = ('user','twitter_account','api_key','api_secret', 'notification_sender', 'notification_to',
                   'custom_css','logo','preview_custom_css','preview_logo', 'public_internal_url', 'user_theme_selection')

class ScheduledMaintenanceForm(forms.ModelForm):
    def __init__(self, user, *args, **kw):
        super(forms.ModelForm, self).__init__(*args, **kw)
        self.fields.keyOrder = ['scheduled_to','time_estimate','message', 'total_downtime', 'created_at', 'updated_at']
    scheduled_to = forms.DateTimeField(required=True,
                                        help_text="Date format is: YYYY-mm-dd HH:ii:ss")
    created_at = forms.DateTimeField(required=False)
    updated_at = forms.DateTimeField(required=False)

    time_estimate = forms.IntegerField(help_text="Used units: minutes")
    total_downtime = forms.FloatField(widget=forms.TextInput(attrs=dict({'class':'disabled', 'readonly':'readonly', 'disabled':'disabled' })), required=False)

    class Meta:
        model = ScheduledMaintenance
        exclude = ('module', 'site_config', 'status')

class ScheduledMaintenanceTemplateForm(forms.ModelForm):
    def __init__(self, user, *args, **kw):
        super(forms.ModelForm, self).__init__(*args, **kw)
        self.fields.keyOrder = ['scheduled_to','time_estimate','message']
    scheduled_to = forms.DateTimeField(required=True,
        help_text="Date format is: YYYY-mm-dd HH:ii:ss")

    class Meta:
        model = ScheduledMaintenance
        exclude = ('module', 'site_config', 'status', 'total_downtime', 'created_at', 'updated_at')

class ModuleForm(forms.ModelForm):
    def __init__(self, user, *args, **kw):
        existing = False
        if kw.has_key('instance'):
            existing = True
        super(forms.ModelForm, self).__init__(*args, **kw)
        self.fields.keyOrder = ['module_type','name','description', 'host', 'url', 'site_config', 'tags', 'expected_status', 'search_keyword', 'check_port', 'public']

        self.fields['site_config'].choices = [ (o.pk, str(o) ) for o in SiteConfig.objects.filter(user=user)]


    check_port = forms.ChoiceField(choices=PORT_CHECK_OPTIONS, required=False, widget=forms.Select(attrs=dict({'class':'check_port'})))
    expected_status = forms.IntegerField(initial=200, required=False, widget=forms.TextInput(attrs=dict({'class':'expected_status'})),
                                        help_text="HTTP response status code.")
    search_keyword = forms.CharField(required=False, widget=forms.TextInput(attrs=dict({'class':'search_keyword'})),
                                        help_text="Keyword or regex to search for in the result page.")

    status = forms.CharField(widget=forms.TextInput(attrs=dict({'class':'disabled', 'readonly':'readonly', 'disabled':'disabled' })), required=False)

    class Meta:
        model = Module


class StatusSiteCustomizationForm(forms.Form):
    logo = forms.ImageField(required=False)
    custom_css = forms.CharField(widget=forms.Textarea, required=False)
    site_config_id = forms.CharField(widget=forms.HiddenInput)

class StatusSiteDomainForm(forms.ModelForm):
    def __init__(self, user, *args, **kw):
        super(forms.ModelForm, self).__init__(*args, **kw)
        self.fields['site_config'].choices = [ (o.pk, str(o) ) for o in SiteConfig.objects.filter(user=user)]

    class Meta:
        model = StatusSiteDomain
