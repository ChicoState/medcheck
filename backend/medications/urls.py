from django.urls import path

from . import views

urlpatterns = [
    path("csrf/", views.csrf_token),
    path("auth/register/", views.register),
    path("auth/login/", views.login_view),
    path("auth/logout/", views.logout_view),
    path("auth/me/", views.current_user),
    path("medications/", views.medications),
]
