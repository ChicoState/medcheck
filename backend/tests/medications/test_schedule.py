import json
from typing import Any

import pytest
from django.contrib.auth import get_user_model
from django.test import Client
from django.utils import timezone

from medications.models import Medication, MedicationDose, MedicationSchedule, SavedMedication

pytestmark = pytest.mark.django_db


def login_client(email: str) -> Any:
    user = get_user_model().objects.create_user(
        username=email,
        email=email,
        password="a-strong-password",
    )
    client = Client()
    assert client.login(username=email, password="a-strong-password")
    return client, user


def save_medication(user: Any, name: str, external_id: str) -> None:
    medication = Medication.objects.create(
        provider="openfda",
        external_id=external_id,
        display_name=name,
        fetched_at=timezone.now(),
    )
    SavedMedication.objects.create(user=user, medication=medication)


def test_schedule_requires_authentication():
    client: Any = Client()
    response = client.get("/api/medications/schedule/")

    assert response.status_code == 401
    assert MedicationSchedule.objects.count() == 0  # pyright: ignore[reportAttributeAccessIssue]


def test_schedule_only_returns_doses_for_the_account_saved_medications():
    client, user = login_client("member@example.com")
    save_medication(user, "Vitamin D", "00653b7c-7099-487e-9a01-e89781c21323")
    save_medication(user, "Atorvastatin", "10653b7c-7099-487e-9a01-e89781c21323")

    first_response = client.get("/api/medications/schedule/")
    second_response = client.get("/api/medications/schedule/")

    assert first_response.status_code == 200
    assert first_response.json() == second_response.json()
    assert (
        MedicationSchedule.objects.filter(  # pyright: ignore[reportAttributeAccessIssue]
            user=user
        ).count()
        == 1
    )
    assert (
        MedicationDose.objects.filter(  # pyright: ignore[reportAttributeAccessIssue]
            schedule__user=user
        ).count()
        == 12
    )
    assert first_response.json()["schedule"]["Wednesday"][1]["name"] == "Atorvastatin"
    visible_names = {
        dose["name"] for doses in first_response.json()["schedule"].values() for dose in doses
    }
    assert visible_names == {"Vitamin D", "Atorvastatin"}


def test_schedules_are_isolated_between_users():
    first_client, first_user = login_client("first@example.com")
    second_client, second_user = login_client("second@example.com")
    save_medication(first_user, "Vitamin D", "20653b7c-7099-487e-9a01-e89781c21323")
    save_medication(second_user, "Lisinopril", "30653b7c-7099-487e-9a01-e89781c21323")

    first_client.get("/api/medications/schedule/")
    second_client.get("/api/medications/schedule/")

    assert MedicationSchedule.objects.filter(  # pyright: ignore[reportAttributeAccessIssue]
        user=first_user
    ).exists()
    assert MedicationSchedule.objects.filter(  # pyright: ignore[reportAttributeAccessIssue]
        user=second_user
    ).exists()
    first_names = {
        dose["name"]
        for doses in first_client.get("/api/medications/schedule/").json()["schedule"].values()
        for dose in doses
    }
    second_names = {
        dose["name"]
        for doses in second_client.get("/api/medications/schedule/").json()["schedule"].values()
        for dose in doses
    }
    assert first_names == {"Vitamin D"}
    assert second_names == {"Lisinopril"}


def test_schedule_endpoint_rejects_non_get_requests():
    client, _ = login_client("member@example.com")

    response = client.post(
        "/api/medications/schedule/",
        data=json.dumps({}),
        content_type="application/json",
    )

    assert response.status_code == 405
