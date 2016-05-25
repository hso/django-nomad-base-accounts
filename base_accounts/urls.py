from django.conf.urls import url
from django.contrib.auth.decorators import login_required
from base_accounts.views import LoginFormView
from base_accounts.views import LogoutView
from base_accounts.views import PostLoginRedirectView
from base_accounts.views import SignupFormView
from base_accounts.views import UpdateEmailFormView
from base_accounts.views import UpdatePasswordFormView
from base_accounts.views import confirm_email_address


urlpatterns = [
    url(r'^login/$', LoginFormView.as_view(), name='login'),
    url(r'^post-login/$', PostLoginRedirectView.as_view(), name='post_login'),
    url(r'^signup/$', SignupFormView.as_view(), name='signup'),
    url(r'^settings/email/$', login_required(UpdateEmailFormView.as_view()), name='settings_update_email'),
    url(r'^settings/password/$', login_required(UpdatePasswordFormView.as_view()), name='settings_update_password'),
    url(r'^confirm/(?P<token>.+)/', confirm_email_address, name='confirm_email_address'),
    url(r'^logout/$', login_required(LogoutView.as_view()), name="logout"),
]
