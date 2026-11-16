import json
from datetime import UTC, datetime
from typing import Any, cast
from uuid import uuid4

import pytest
from django.contrib.auth import get_user_model
from django.test import Client as DjangoClient

from medications.models import Medication, MedicationDose, MedicationSchedule, SavedMedication

pytestmark = pytest.mark.django_db
URL = "/api/medications/schedule/"
Client = cast(Any, DjangoClient)


def signed_in(email):
    user = get_user_model().objects.create_user(
        username=email, email=email, password="test-password"
    )
    client = Client()
    client.force_login(user)
    return client, user


def test_schedule_requires_authentication_and_get():
    assert Client().get(URL).status_code == 401
    client, _ = signed_in("one@example.com")
    assert client.post(URL).status_code == 405
    assert MedicationSchedule.objects.count() == 0


def test_schedule_is_seeded_once_and_private():
    first, first_user = signed_in("one@example.com")
    second, _ = signed_in("two@example.com")
    initial = first.get(URL)
    assert initial.status_code == 200
    assert list(initial.json()["schedule"]) == [
        "Monday",
        "Tuesday",
        "Wednesday",
        "Thursday",
        "Friday",
        "Saturday",
        "Sunday",
    ]
    assert initial.json()["schedule"]["Wednesday"][2]["name"] == "Atorvastatin"
    assert first.get(URL).json() == initial.json()
    assert MedicationDose.objects.filter(schedule__user=first_user).count() == 12
    other = second.get(URL).json()["schedule"]
    assert other["Wednesday"][2]["id"] != initial.json()["schedule"]["Wednesday"][2]["id"]
    MedicationDose.objects.filter(schedule__user=first_user).delete()
    assert first.get(URL).json()["schedule"]["Wednesday"] == []


def test_saved_medicine_schedule_can_be_added_updated_and_removed():
    first, user = signed_in("one@example.com")
    second, _ = signed_in("two@example.com")
    medication = Medication.objects.create(
        provider="openfda",
        external_id=uuid4(),
        display_name="Example tablet",
        fetched_at=datetime.now(UTC),
    )
    saved = SavedMedication.objects.create(user=user, medication=medication)
    endpoint = f"{URL}{saved.pk}/"
    payload = {"days": [0, 2, 4, 5, 6], "period": "morning", "time": "08:15"}
    assert (
        Client().put(endpoint, json.dumps(payload), content_type="application/json").status_code
        == 401
    )
    assert (
        second.put(endpoint, json.dumps(payload), content_type="application/json").status_code
        == 404
    )
    assert (
        first.put(endpoint, json.dumps(payload), content_type="application/json").status_code == 200
    )
    assert first.get("/api/saved-medications/").json()["data"][0]["schedulePlan"] == payload
    assert (
        MedicationDose.objects.filter(schedule__user=user, saved_medication__isnull=True).count()
        == 0
    )
    assert MedicationDose.objects.filter(saved_medication=saved).count() == 5
    assert first.get(URL).json()["schedule"]["Saturday"][0]["name"] == "Example tablet"
    assert first.get(URL).json()["schedule"]["Sunday"][0]["name"] == "Example tablet"
    payload = {"days": [1], "period": "evening", "time": "20:00"}
    assert (
        first.put(endpoint, json.dumps(payload), content_type="application/json").status_code == 200
    )
    assert MedicationDose.objects.filter(saved_medication=saved).count() == 1
    assert first.get(URL).json()["schedule"]["Tuesday"][-1]["name"] == "Example tablet"
    assert first.get(URL).json()["schedule"]["Tuesday"][-1]["food"] is None
    assert first.delete(endpoint).status_code == 204
    assert MedicationDose.objects.filter(saved_medication=saved).count() == 0


@pytest.mark.parametrize(
    "payload",
    [
        {"days": [], "period": "morning", "time": "08:00"},
        {"days": [7], "period": "morning", "time": "08:00"},
        {"days": [True], "period": "morning", "time": "08:00"},
        {"days": [0, 0], "period": "morning", "time": "08:00"},
        {"days": [0], "period": "night", "time": "08:00"},
        {"days": [0], "period": "morning", "time": "not-a-time"},
        {"days": [0], "period": "morning", "time": "08:00:00"},
    ],
)
def test_schedule_rejects_invalid_choices(payload):
    client, user = signed_in("one@example.com")
    medication = Medication.objects.create(
        provider="openfda",
        external_id=uuid4(),
        display_name="Example tablet",
        fetched_at=datetime.now(UTC),
    )
    saved = SavedMedication.objects.create(user=user, medication=medication)
    response = client.put(f"{URL}{saved.pk}/", json.dumps(payload), content_type="application/json")
    assert response.status_code == 400
    assert MedicationDose.objects.filter(saved_medication=saved).count() == 0
