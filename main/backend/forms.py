from django import forms
from django.contrib.auth.models import User
from django.utils.translation import ugettext_lazy as _


class ProfileForm(forms.Form):
    username = forms.RegexField(regex=r'^[\w.@+-]+$',
        max_length=30,
        widget=forms.TextInput(attrs={'class':'disabled', 'readonly':'readonly', 'disabled':'disabled' }),
        label=_("Username"),
        error_messages={'invalid': _("This value may contain only letters, numbers and @/./+/-/_ characters.")},
        required=False)
    email = forms.EmailField(widget=forms.TextInput(attrs=dict({'class':'disabled', 'readonly':'readonly', 'disabled':'disabled' },
        maxlength=75)),
        label=_("E-mail"), required=False)
    first_name = forms.CharField(max_length=30, required=False)
    last_name = forms.CharField(max_length=30, required=False)
    password1 = forms.CharField(widget=forms.PasswordInput(render_value=False),
        label=_("Password"), required=False)
    password2 = forms.CharField(widget=forms.PasswordInput(render_value=False),
        label=_("Password (again)"), required=False)



    def clean(self):
        if 'password1' in self.cleaned_data and 'password2' in self.cleaned_data:
            if self.cleaned_data['password1'] != self.cleaned_data['password2']:
                raise forms.ValidationError(_("The two password fields didn't match."))
        return self.cleaned_data