from django.urls import path

from accounts import views

urlpatterns = [
    path("auth/csrf/", views.csrf),
    path("auth/register/", views.RegisterView.as_view()),
    path("auth/login/", views.LoginView.as_view()),
    path("auth/logout/", views.LogoutView.as_view()),
    path("me/", views.MeView.as_view()),
    path("medications/", views.MedicationsView.as_view()),
    path("medications/<int:medication_id>/", views.MedicationDetailView.as_view()),
]
