import json
from typing import Any

import pytest
from django.contrib.auth import get_user_model
from django.test import Client

from medications.models import MedicationDose, MedicationSchedule

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


def test_schedule_requires_authentication():
    client: Any = Client()
    response = client.get("/api/medications/schedule/")

    assert response.status_code == 401
    assert MedicationSchedule.objects.count() == 0  # pyright: ignore[reportAttributeAccessIssue]


def test_first_schedule_read_seeds_and_persists_the_account_schedule():
    client, user = login_client("member@example.com")

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
    assert first_response.json()["schedule"]["Wednesday"][2]["name"] == "Atorvastatin"


def test_schedules_are_isolated_between_users():
    first_client, first_user = login_client("first@example.com")
    second_client, second_user = login_client("second@example.com")

    first_client.get("/api/medications/schedule/")
    second_client.get("/api/medications/schedule/")

    assert MedicationSchedule.objects.filter(  # pyright: ignore[reportAttributeAccessIssue]
        user=first_user
    ).exists()
    assert MedicationSchedule.objects.filter(  # pyright: ignore[reportAttributeAccessIssue]
        user=second_user
    ).exists()
    first_ids = {
        dose["id"]
        for doses in first_client.get("/api/medications/schedule/").json()["schedule"].values()
        for dose in doses
    }
    second_ids = {
        dose["id"]
        for doses in second_client.get("/api/medications/schedule/").json()["schedule"].values()
        for dose in doses
    }
    assert first_ids.isdisjoint(second_ids)


def test_schedule_endpoint_rejects_non_get_requests():
    client, _ = login_client("member@example.com")

    response = client.post(
        "/api/medications/schedule/",
        data=json.dumps({}),
        content_type="application/json",
    )

    assert response.status_code == 405
