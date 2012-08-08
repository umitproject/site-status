import datetime
from django import forms
from django.contrib.admin import widgets
from django.core import validators
from django.contrib.auth.models import User
from django.utils.translation import ugettext_lazy as _
from main.models import SiteConfig, UserProfile, Module, StatusSiteDomain, PORT_CHECK_OPTIONS


class ProfileForm(forms.ModelForm):
    class Meta:
        model=UserProfile
        exclude=('user',)

    username = forms.RegexField(regex=r'^[\w.@+-]+$',
        max_length=30,
        widget=forms.TextInput(attrs={'class':'disabled', 'readonly':'readonly', 'disabled':'disabled' }),
        label=_("Username"),
        error_messages={'invalid': _("This value may contain only letters, numbers and @/./+/-/_ characters.")},
        required=False)
    email = forms.EmailField(widget=forms.TextInput(attrs=dict({'class':'disabled', 'readonly':'readonly', 'disabled':'disabled' },
        maxlength=75)),
        label=_("E-mail"),
        required=False,
        validators=[validators.validate_email],
        error_messages={'invalid': _("Invalid email address.")})
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
        self.fields.keyOrder = ['username', 'email', 'first_name', 'last_name','birth_date', 'address', 'city', 'country',
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
        exclude = ('user','twitter_account','api_key','api_secret')

class ModuleForm(forms.ModelForm):
    def __init__(self, user, *args, **kw):
        existing = False
        if kw.has_key('instance'):
            existing = True
        super(forms.ModelForm, self).__init__(*args, **kw)
        self.fields.keyOrder = ['module_type','name','description', 'host', 'url', 'site_config', 'tags', 'expected_status', 'search_keyword', 'check_port']

        self.fields['site_config'].choices = [ (o.pk, str(o) ) for o in SiteConfig.objects.filter(user=user)]


    check_port = forms.ChoiceField(choices=PORT_CHECK_OPTIONS, required=False, widget=forms.Select(attrs=dict({'class':'check_port'})))
    expected_status = forms.IntegerField(initial=200, required=False, widget=forms.TextInput(attrs=dict({'class':'expected_status'})))
    search_keyword = forms.CharField(required=False, widget=forms.TextInput(attrs=dict({'class':'search_keyword'})))

    status = forms.CharField(widget=forms.TextInput(attrs=dict({'class':'disabled', 'readonly':'readonly', 'disabled':'disabled' })), required=False)


    class Meta:
        model = Module

class StatusSiteDomainForm(forms.ModelForm):
    def __init__(self, user, *args, **kw):
        super(forms.ModelForm, self).__init__(*args, **kw)
        self.fields['site_config'].choices = [ (o.pk, str(o) ) for o in SiteConfig.objects.filter(user=user)]

    class Meta:
        model = StatusSiteDomain
