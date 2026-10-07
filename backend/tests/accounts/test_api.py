import pytest
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient

from accounts.models import HealthProfile, Medication


@pytest.mark.django_db
def test_registration_creates_a_session_and_private_profile() -> None:
    client = APIClient()

    response = client.post(
        "/api/auth/register/",
        {"email": "person@example.com", "password": "safe-not-a-real-password"},
        format="json",
    )

    assert response.status_code == 201
    assert response.data["email"] == "person@example.com"
    assert client.get("/api/me/").status_code == 200


@pytest.mark.django_db
def test_profile_and_medications_are_private_to_the_signed_in_user() -> None:
    user_model = get_user_model()
    owner = user_model.objects.create_user(email="owner@example.com", password="safe-password")
    other = user_model.objects.create_user(email="other@example.com", password="safe-password")
    owner_profile = HealthProfile.objects.create(user=owner)
    medication = Medication.objects.create(profile=owner_profile, name="Example medicine")
    client = APIClient()
    client.force_login(owner)

    profile_response = client.patch(
        "/api/me/", {"date_of_birth": "1990-01-15", "gender": "nonbinary"}, format="json"
    )
    medication_response = client.post(
        "/api/medications/", {"name": "  Sample medicine  "}, format="json"
    )

    assert profile_response.status_code == 200
    assert medication_response.status_code == 201
    assert medication_response.data["name"] == "Sample medicine"

    client.force_login(other)
    assert client.delete(f"/api/medications/{medication.pk}/").status_code == 404


@pytest.mark.django_db
def test_login_failure_and_unauthenticated_requests_use_safe_errors() -> None:
    user_model = get_user_model()
    user_model.objects.create_user(email="person@example.com", password="safe-password")
    client = APIClient()

    login_response = client.post(
        "/api/auth/login/",
        {"email": "person@example.com", "password": "wrong-password"},
        format="json",
    )
    profile_response = client.get("/api/me/")

    assert login_response.status_code == 400
    assert login_response.data["error"]["code"] == "INVALID_CREDENTIALS"
    assert profile_response.status_code == 401
    assert profile_response.data["error"]["code"] == "NOT_AUTHENTICATED"
