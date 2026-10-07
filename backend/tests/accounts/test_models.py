"""Database behavior for private account health data."""

import pytest
from django.contrib.auth import get_user_model
from django.db import IntegrityError

from accounts.models import HealthProfile, Medication


@pytest.mark.django_db
def test_email_identifies_a_user_uniquely() -> None:
    user_model = get_user_model()
    user_model.objects.create_user(email="person@example.com", password="not-a-real-password")

    with pytest.raises(IntegrityError):
        user_model.objects.create_user(email="person@example.com", password="another-password")


@pytest.mark.django_db
def test_profile_keeps_optional_health_details_separate_from_user() -> None:
    user_model = get_user_model()
    user = user_model.objects.create_user(
        email="person@example.com", password="not-a-real-password"
    )

    profile = HealthProfile.objects.create(
        user=user,
        date_of_birth="1990-01-15",
        gender="nonbinary",
    )

    assert profile.user == user
    assert str(profile.date_of_birth) == "1990-01-15"
    assert profile.gender == "nonbinary"

    with pytest.raises(IntegrityError):
        HealthProfile.objects.create(user=user)


@pytest.mark.django_db
def test_medications_are_owned_by_and_deleted_with_the_profile() -> None:
    user_model = get_user_model()
    user = user_model.objects.create_user(
        email="person@example.com", password="not-a-real-password"
    )
    profile = HealthProfile.objects.create(user=user)
    medication = Medication.objects.create(profile=profile, name="Example medicine")

    profile.delete()

    assert not Medication.objects.filter(pk=medication.pk).exists()
