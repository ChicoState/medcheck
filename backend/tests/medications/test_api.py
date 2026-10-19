import json
from datetime import timedelta
from typing import Any, cast
from unittest.mock import patch

import pytest
from django.contrib.auth import get_user_model
from django.core.cache import cache
from django.test import Client as DjangoClient
from django.utils import timezone

from medications.models import Medication
from medications.provider import ProviderError

pytestmark = pytest.mark.django_db
Client = cast(Any, DjangoClient)

LABEL_ID = "00653b7c-7099-487e-9a01-e89781c21323"
LABEL = {
    "provider": "openfda",
    "externalId": LABEL_ID,
    "displayName": "Ibuprofen Dye Free",
    "genericName": "IBUPROFEN",
    "brandNames": ["Ibuprofen Dye Free"],
    "activeIngredients": ["Ibuprofen USP, 200 mg"],
    "dosageForms": [],
    "routes": ["ORAL"],
    "rxcui": "310965",
    "sections": [{"key": "warnings", "title": "Warnings", "text": "Ask a doctor."}],
    "labelEffectiveDate": "2026-04-29",
    "datasetUpdatedAt": "2026-10-16",
    "sourceUrl": "https://api.fda.gov/drug/label.json?search=set_id%3A%2200653b7c-7099-487e-9a01-e89781c21323%22",
}


@pytest.fixture(autouse=True)
def clear_cache():
    cache.clear()


def signed_in_client(email="one@example.com"):
    user = get_user_model().objects.create_user(
        username=email, email=email, password="strong-password-123"
    )
    client = Client(enforce_csrf_checks=True)
    client.force_login(user)
    token = client.get("/api/auth/csrf/").json()["csrfToken"]
    return client, token


def test_search_returns_normalized_results_and_rejects_bad_input():
    with patch("medications.views.search_labels") as search:
        search.return_value = ([LABEL], 1)
        response = Client().get("/api/medications/?q=ibuprofen")
        assert response.status_code == 200
        assert response.json()["data"][0]["externalId"] == LABEL_ID
        assert response.json()["pagination"]["hasNextPage"] is False
        assert Client().get("/api/medications/?q=").status_code == 400
        assert Client().get("/api/medications/?q=test&page=0").status_code == 400
        assert search.call_count == 1


def test_detail_save_list_and_remove_are_private_and_persistent():
    first, token = signed_in_client()
    second, second_token = signed_in_client("two@example.com")
    with patch("medications.views.get_label", return_value=LABEL):
        detail = first.get(f"/api/medications/openfda/{LABEL_ID}/")
        assert detail.status_code == 200
        assert detail.json()["isSaved"] is False

        url = "/api/saved-medications/"
        payload = json.dumps({"provider": "openfda", "externalId": LABEL_ID})
        assert first.post(url, payload, content_type="application/json").status_code == 403
        saved = first.post(url, payload, content_type="application/json", HTTP_X_CSRFTOKEN=token)
        assert saved.status_code == 201
        assert (
            first.post(
                url, payload, content_type="application/json", HTTP_X_CSRFTOKEN=token
            ).status_code
            == 200
        )
        saved_id = saved.json()["savedId"]

    assert first.get(url).json()["data"][0]["savedId"] == saved_id
    assert second.get(url).json()["data"] == []
    assert Client().get(url).status_code == 401
    assert second.delete(f"{url}{saved_id}/", HTTP_X_CSRFTOKEN=second_token).status_code == 404
    assert first.delete(f"{url}{saved_id}/", HTTP_X_CSRFTOKEN=token).status_code == 204
    assert first.get(url).json()["data"] == []


def test_provider_failure_is_safe():
    with patch("medications.views.search_labels", side_effect=ProviderError("unavailable")):
        response = Client().get("/api/medications/?q=ibuprofen")
    assert response.status_code == 503
    assert response.json()["error"]["code"] == "PROVIDER_UNAVAILABLE"


def test_search_cache_and_saved_state_are_per_user():
    first, token = signed_in_client()
    second, _ = signed_in_client("two@example.com")
    with patch("medications.views.search_labels", return_value=([LABEL], 1)) as search:
        assert first.get("/api/medications/?q=ibuprofen").json()["data"][0]["isSaved"] is False
        with patch("medications.views.get_label", return_value=LABEL):
            first.post(
                "/api/saved-medications/",
                json.dumps({"provider": "openfda", "externalId": LABEL_ID}),
                content_type="application/json",
                HTTP_X_CSRFTOKEN=token,
            )
        assert first.get("/api/medications/?q=ibuprofen").json()["data"][0]["isSaved"] is True
        assert second.get("/api/medications/?q=ibuprofen").json()["data"][0]["isSaved"] is False
        assert search.call_count == 1


def test_stale_label_is_available_when_provider_fails():
    with patch("medications.views.get_label", return_value=LABEL):
        assert Client().get(f"/api/medications/openfda/{LABEL_ID}/").status_code == 200
    Medication.objects.filter(external_id=LABEL_ID).update(
        fetched_at=timezone.now() - timedelta(days=2)
    )
    with patch("medications.views.get_label", side_effect=ProviderError("unavailable")):
        response = Client().get(f"/api/medications/openfda/{LABEL_ID}/")
    assert response.status_code == 200
    assert response.json()["isStale"] is True


def test_invalid_save_and_search_throttle():
    first, token = signed_in_client()
    url = "/api/saved-medications/"
    assert (
        first.post(
            url,
            json.dumps({"provider": "openfda", "externalId": "not-a-uuid"}),
            content_type="application/json",
            HTTP_X_CSRFTOKEN=token,
        ).status_code
        == 400
    )
    with patch("medications.views.search_labels", return_value=([], 0)):
        for _ in range(60):
            assert first.get("/api/medications/?q=ibuprofen").status_code == 200
        assert first.get("/api/medications/?q=ibuprofen").status_code == 429
