from datetime import UTC, datetime
from typing import Any, cast
from unittest.mock import patch
from uuid import uuid4

import pytest
from django.contrib.auth import get_user_model
from django.test import Client as DjangoClient

from medications.models import Medication, SavedMedication
from medications.provider import ProviderError

Client = cast(Any, DjangoClient)
pytestmark = pytest.mark.django_db
URL = "/api/saved-medications/interactions/"


def member(email="one@example.com"):
    user = get_user_model().objects.create_user(
        username=email, email=email, password="test-password"
    )
    client = Client()
    client.force_login(user)
    return client, user


def save(user, name, generic, text):
    medication = Medication.objects.create(
        provider="openfda",
        external_id=uuid4(),
        display_name=name,
        generic_name=generic,
        brand_names=[name],
        active_ingredients=[],
        label_sections=[{"key": "drug_interactions", "text": text}] if text is not None else [],
        fetched_at=datetime.now(UTC),
    )
    SavedMedication.objects.create(user=user, medication=medication)


def test_saved_interactions_require_account_and_two_labels():
    assert Client().get(URL).status_code == 401
    client, user = member()
    assert client.get(URL).json()["status"] == "incomplete"
    save(user, "Aspirin", "aspirin", "Ask a pharmacist.")
    assert client.get(URL).json()["status"] == "incomplete"


def test_saved_interactions_clear_only_when_all_pairs_checked():
    client, user = member()
    save(user, "Aspirin", "aspirin", "Ask a pharmacist.")
    save(user, "Metformin", "metformin", "Check kidney function.")
    result = client.get(URL).json()
    assert result["status"] == "clear"
    assert result["pairsChecked"] == result["totalPairs"] == 1
    assert result["matches"] == []


def test_saved_interactions_report_matches_and_incomplete_labels():
    client, user = member()
    save(user, "Aspirin", "aspirin", "Avoid combining with metformin.")
    save(user, "Metformin", "metformin", "Check kidney function.")
    result = client.get(URL).json()
    assert result["status"] == "match"
    assert result["matches"][0]["names"] == ["Aspirin", "Metformin"]
    assert result["matches"][0]["findings"][0]["sourceUrl"].startswith("https://api.fda.gov/")
    save(user, "Third", "third", None)
    result = client.get(URL).json()
    assert result["status"] == "match"
    assert result["pairsChecked"] < result["totalPairs"]


def test_saved_interactions_isolate_accounts_and_never_green_with_missing_section():
    first, first_user = member()
    second, second_user = member("two@example.com")
    save(first_user, "Aspirin", "aspirin", "Ask a pharmacist.")
    save(first_user, "Unknown", "unknown", None)
    save(second_user, "Metformin", "metformin", "Check kidney function.")
    assert first.get(URL).json()["status"] == "incomplete"
    assert second.get(URL).json()["totalPairs"] == 0


def test_saved_interactions_provider_failure_is_incomplete():
    client, user = member()
    save(user, "Aspirin", "aspirin", "Ask a pharmacist.")
    save(user, "Metformin", "metformin", "Check kidney function.")
    with patch("medications.views._medication", side_effect=ProviderError()):
        result = client.get(URL).json()
    assert result["status"] == "incomplete"
    assert result["pairsChecked"] == 0


def test_saved_interactions_caps_large_libraries():
    client, user = member()
    for index in range(11):
        save(user, f"Medicine {index}", f"generic {index}", "Check the label.")
    result = client.get(URL).json()
    assert result["status"] == "incomplete"
    assert result["reason"] == "too_many"
    assert result["pairsChecked"] == 0
