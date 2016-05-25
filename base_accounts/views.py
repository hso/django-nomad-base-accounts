# -*- coding: utf-8 -*-

from django.views.generic import View, FormView
from django.contrib.auth import login, logout
from django.shortcuts import get_object_or_404
from django.shortcuts import redirect
from django.shortcuts import resolve_url
from django.utils.translation import ugettext as _
from django.utils.timezone import now
from django.conf import settings
from django.http import Http404
from django.core import signing
from django.core.urlresolvers import reverse
from django.contrib.auth import get_user_model

from base_accounts.forms import SignupForm, LoginForm, UpdateEmailForm, UpdatePasswordForm


from django.contrib import messages
try:
    from django.contrib.messages.views import SuccessMessageMixin
except:
    # This mixin was added to Django 1.6, we define it for backwards compatibility

    class SuccessMessageMixin(object):
        """
        Adds a success message on successful form submission.
        """
        success_message = ''

        def form_valid(self, form):
            response = super(SuccessMessageMixin, self).form_valid(form)
            success_message = self.get_success_message(form.cleaned_data)
            if success_message:
                messages.success(self.request, success_message)
            return response

        def get_success_message(self, cleaned_data):
            return self.success_message % cleaned_data


class ErrorMessageRedirectMixin(object):
    """Redirect to error url or next param if exists, converting form error strs to sys msgs"""

    def get_error_url(self):
        error_url = None

        if getattr(self, 'error_url', None):  # Error URL from object property
            error_url = redirect(self.error_url)
        elif self.request.POST.get('next'):  # Error URL contains a next param
            error_url = redirect("%s?next=%s" % (reverse_lazy('login'),
                                                 self.request.POST.get('next')))
        return error_url

    def form_invalid(self, form):
        error_url = self.get_error_url()

        # If error url, convert form errors to sys msgs and redirect
        if error_url:
            for msg in form.errors.values():
                messages.error(self.request, _(msg[0]))
            return error_url

        return super(ErrorMessageRedirectMixin, self).form_invalid(form)


class NextRedirectMixin(object):
    """Manages redirection on post-login or post-signup"""

    def get_success_url(self):
        if self.request.POST.get('next'):
            self.success_url = self.request.POST.get('next')
        return super(NextRedirectMixin, self).get_success_url()

    def get_context_data(self, **kwargs):
        ctxt = super(NextRedirectMixin, self).get_context_data(**kwargs)
        ctxt['next'] = self.request.GET.get('next') or self.request.POST.get('next') or ''
        return ctxt


class SignupFormView(SuccessMessageMixin, NextRedirectMixin, FormView):
    form_class = SignupForm
    template_name = 'base_accounts/signup.html'
    success_message = _("Welcome!")

    def get_success_url(self):
        success_url = getattr(settings,
                              'BASE_ACCOUNTS_SIGNUP_REDIRECT_URL',
                              settings.LOGIN_REDIRECT_URL)
        self.success_url = resolve_url(success_url)
        return super(SignupFormView, self).get_success_url()

    def get_form_kwargs(self):
        """Form uses request to signup"""
        kwargs = super(SignupFormView, self).get_form_kwargs()
        kwargs.update({'request': self.request})
        return kwargs

    def form_valid(self, form):
        form.save()
        return super(SignupFormView, self).form_valid(form)


class LoginFormView(SuccessMessageMixin, ErrorMessageRedirectMixin, NextRedirectMixin, FormView):
    form_class = LoginForm
    template_name = 'base_accounts/login.html'
    success_message = _("You have logged in")

    def get_success_url(self):
        success_url = getattr(settings,
                              'BASE_ACCOUNTS_LOGIN_REDIRECT_URL',
                              settings.LOGIN_REDIRECT_URL)
        self.success_url = resolve_url(success_url)
        return super(LoginFormView, self).get_success_url()

    def get_form_kwargs(self):
        """Form uses request to login"""
        kwargs = super(LoginFormView, self).get_form_kwargs()
        kwargs.update({'request': self.request})
        return kwargs


class UpdateEmailFormView(SuccessMessageMixin, ErrorMessageRedirectMixin, FormView):
    """Updates user model with new provided email"""
    form_class = UpdateEmailForm
    template_name = 'base_accounts/update_email.html'
    success_message = _('You have updated your email successfully')

    def get_success_url(self):
        success_url = getattr(settings,
                              'BASE_ACCOUNTS_UPDATE_EMAIL_REDIRECT_URL',
                              reverse('settings_update_email'))
        self.success_url = resolve_url(success_url)
        return super(UpdateEmailFormView, self).get_success_url()

    def get_error_url(self):
        error_url = getattr(settings,
                            'BASE_ACCOUNTS_UPDATE_EMAIL_ERROR_REDIRECT_URL',
                            reverse('settings_update_email'))
        self.error_url = resolve_url(error_url)
        return super(UpdateEmailFormView, self).get_error_url()

    def get_form_kwargs(self):
        """Form uses request to fetch current user"""
        kwargs = super(UpdateEmailFormView, self).get_form_kwargs()
        kwargs.update({'request': self.request})
        return kwargs

    def form_valid(self, form):
        new_email = form.cleaned_data.get('email')
        if self.request.user.email != new_email:
            self.request.user.email = new_email
            self.request.user.confirmed = None
            self.request.user.save()
        return super(UpdateEmailFormView, self).form_valid(form)


class UpdatePasswordFormView(SuccessMessageMixin, ErrorMessageRedirectMixin, FormView):
    """Updates user model with new provided password"""
    form_class = UpdatePasswordForm
    template_name = 'base_accounts/update_password.html'
    success_message = _('You have updated your password successfully')

    def get_success_url(self):
        success_url = getattr(settings,
                              'BASE_ACCOUNTS_UPDATE_PASSWORD_REDIRECT_URL',
                              reverse('settings_update_password'))
        self.success_url = resolve_url(success_url)
        return super(UpdatePasswordFormView, self).get_success_url()

    def get_error_url(self):
        error_url = getattr(settings,
                            'BASE_ACCOUNTS_UPDATE_PASSWORD_ERROR_REDIRECT_URL',
                            reverse('settings_update_password'))
        self.error_url = resolve_url(error_url)
        return super(UpdatePasswordFormView, self).get_error_url()

    def get_form_kwargs(self):
        """Form uses request to fetch current user"""
        kwargs = super(UpdatePasswordFormView, self).get_form_kwargs()
        kwargs.update({'request': self.request})
        return kwargs

    def form_valid(self, form):
        """Use model method to update new password"""
        self.request.user.set_password(form.cleaned_data['password1'])
        self.request.user.save()
        # Django >= 1.7 requires this call to stay logged in.
        # More info: https://docs.djangoproject.com/en/1.7/topics/auth/default/#session-invalidation-on-password-change
        from django.contrib import auth
        if hasattr(auth, 'update_session_auth_hash'):
            auth.update_session_auth_hash(self.request, self.request.user)
        return super(UpdatePasswordFormView, self).form_valid(form)


class PostLoginRedirectView(SuccessMessageMixin, View):
    """Used by social login flows (e.g. OAuth)"""
    success_message = _("You have logged in")

    def get_success_url(self):
        success_url = getattr(settings,
                              'BASE_ACCOUNTS_POST_LOGIN_REDIRECT_URL',
                              settings.LOGIN_REDIRECT_URL)
        self.success_url = resolve_url(success_url)
        return super(PostLoginRedirectView, self).get_success_url()

    def dispatch(self, request, *args, **kwargs):
        """Override post-login url if provided"""
        if self.request.GET.get('next'):
            self.success_url = self.request.GET.get('next')
        messages.success(self.request, self.success_message)
        return redirect(self.success_url)


class LogoutView(View):
    """Updates User.first_login field before logout"""

    def get_success_url(self):
        success_url = getattr(settings,
                              'BASE_ACCOUNTS_LOGOUT_REDIRECT_URL',
                              '/')
        self.success_url = resolve_url(success_url)
        return super(LogoutView, self).get_success_url()

    def dispatch(self, request, *args, **kwargs):
        list(messages.get_messages(request))  # Get rid of messages
        user = request.user
        if user.first_login:
            user.first_login = False
            user.save(update_fields=['first_login'])
        logout(request)
        return redirect(self.success_url)


def confirm_email_address(request, token):
    """Confirms user's email address"""
    success_url = getattr(settings, 'BASE_ACCOUNTS_CONFIRM_EMAIL_REDIRECT_URL', '/')
    try:
        pk = signing.loads(token, max_age=3600 * 48, salt='resend_email_confirmation')
    except signing.BadSignature:
        raise Http404
    user = get_object_or_404(get_user_model(), pk=pk)

    if user.confirmed:
        raise Http404

    user.confirmed = now()
    user.save()

    if request.user != user:
        logout(request)

    if not request.user.is_authenticated():
        user.backend = 'django.contrib.auth.backends.ModelBackend'
        login(request, user)

    if user.is_active:
        messages.success(request, _('You have confirmed your email address'))
        return redirect(success_url)
    else:
        messages.success(request, _('Please confirm your email address'))
        return redirect('password_reset_recover')
