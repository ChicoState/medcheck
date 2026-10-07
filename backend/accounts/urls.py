from django.urls import path

from accounts.views import CredentialsView, LogoutView, RegisterView, SessionView

urlpatterns = [
    path("session/", SessionView.as_view(), name="account-session"),
    path("register/", RegisterView.as_view(), name="account-register"),
    path("login/", CredentialsView.as_view(), name="account-login"),
    path("logout/", LogoutView.as_view(), name="account-logout"),
]
