from django import forms
from django.contrib.auth import authenticate, login, get_user_model
from django.utils.translation import ugettext_lazy as _

from base_accounts.utils import create_email_user


class SignupFormMixin(object):

    def clean_email(self, *args, **kwargs):
        data = self.cleaned_data['email']
        if getattr(self, 'clean_email_user_model', None):
            model = self.clean_email_user_model
        else:
            model = self.user_model
        try:
            model.objects.get(email=data)
        except model.DoesNotExist:
            return data
        else:
            raise forms.ValidationError(_("Email is already being used by another user"))

    def save(self, *args, **kwargs):

        # Get model fields
        full_name = self.cleaned_data.get('full_name').lower()
        email = self.cleaned_data.get('email').lower()
        password = self.cleaned_data.get('password')

        # Create new user
        user = create_email_user(email, password, self.user_model, **{'name': full_name})

        # Authenticate and login user
        user = authenticate(username=user.username, password=password)
        login(self.request, user)

        return user


class SignupForm(SignupFormMixin, forms.Form):
    full_name = forms.CharField(label=_('full name'))
    email = forms.EmailField(label=_('email'))
    password = forms.CharField(label=_('password'), widget=forms.PasswordInput)
    tos = forms.BooleanField(label=_('I accept the terms of service'))
    user_model = get_user_model()

    def __init__(self, *args, **kwargs):
        request = kwargs.pop('request', None)
        self.request = request
        return super(SignupForm, self).__init__(*args, **kwargs)


class LoginForm(forms.Form):
    email = forms.EmailField(label=_('email'))
    password = forms.CharField(label=_('password'), widget=forms.PasswordInput)

    def __init__(self, *args, **kwargs):
        request = kwargs.pop('request', None)
        self.request = request
        return super(LoginForm, self).__init__(*args, **kwargs)

    def clean(self, *args, **kwargs):
        cleaned_data = super(LoginForm, self).clean()

        # Get data
        email = cleaned_data.get('email')
        password = cleaned_data.get('password')

        # Return empty cleaned data so form.is_valid() will be False
        if email is None or password is None:
            return cleaned_data

        # Check that email and password match and user is active
        user = authenticate(email=email, password=password)
        if user is None:
            raise forms.ValidationError(_("Please insert both valid email and password"))
        elif not user.is_active:
            raise forms.ValidationError(_("Your account is inactive"))

        # Login user
        login(self.request, user)
        return cleaned_data


class UpdateEmailForm(forms.Form):
    email = forms.EmailField(required=True)
    user_model = get_user_model()

    def __init__(self, *args, **kwargs):
        request = kwargs.pop('request', None)
        self.user = request.user
        return super(UpdateEmailForm, self).__init__(*args, **kwargs)

    def clean_email(self, *args, **kwargs):
        data = self.cleaned_data['email']
        try:
            self.user_model.objects.exclude(id=self.user.id).get(email=data)
        except self.user_model.DoesNotExist:
            return data
        else:
            raise forms.ValidationError(_("Email is already being used by another user"))


class UpdatePasswordForm(forms.Form):
    password1 = forms.CharField(label=_('new password'), widget=forms.PasswordInput,)
    password2 = forms.CharField(label=_('new password (confirm)'), widget=forms.PasswordInput,)
    user_model = get_user_model()

    def __init__(self, *args, **kwargs):
        request = kwargs.pop('request', None)
        self.user = request.user
        super(UpdatePasswordForm, self).__init__(*args, **kwargs)

    def clean_password2(self):
        password1 = self.cleaned_data.get('password1', '')
        password2 = self.cleaned_data['password2']
        if not password1 == password2:
            raise forms.ValidationError(_("Passwords didn't match"))
        return password2
