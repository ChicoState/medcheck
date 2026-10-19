import json
from typing import Any, cast

import pytest
from django.contrib.auth import get_user_model
from django.db import IntegrityError, transaction
from django.test import Client

from medications.models import Medication

TEST_PASSWORD = "a-safe-password-123"  # nosec B105


def csrf_client() -> tuple[Client, str]:
    client = Client(enforce_csrf_checks=True)
    return client, csrf_token(client)


def csrf_token(client: Client) -> str:
    response = cast(Any, client.get("/api/csrf/"))
    assert response.status_code == 200  # nosec B101
    return response.json()["csrfToken"]


def post_json(client: Client, path: str, payload: dict[str, str], token: str):
    return cast(
        Any,
        client.post(
            path,
            data=json.dumps(payload),
            content_type="application/json",
            HTTP_X_CSRFTOKEN=token,
        ),
    )


def get(client: Client, path: str) -> Any:
    return cast(Any, client.get(path))


@pytest.mark.django_db
def test_user_can_sign_in_add_a_medication_and_see_it_after_signing_in_again():
    client, token = csrf_client()

    registration = post_json(
        client,
        "/api/auth/register/",
        {"email": "patient@example.com", "password": TEST_PASSWORD},
        token,
    )
    assert registration.status_code == 201  # nosec B101
    token = csrf_token(client)

    creation = post_json(
        client,
        "/api/medications/",
        {"name": "Lisinopril", "dosage": "10 mg", "frequency": "Once daily"},
        token,
    )
    assert creation.status_code == 201  # nosec B101
    assert creation.json()["name"] == "Lisinopril"  # nosec B101

    logout = post_json(client, "/api/auth/logout/", {}, token)
    assert logout.status_code == 204  # nosec B101

    login = post_json(
        client,
        "/api/auth/login/",
        {"email": "patient@example.com", "password": TEST_PASSWORD},
        token,
    )
    assert login.status_code == 200  # nosec B101

    medications = get(client, "/api/medications/")
    assert medications.status_code == 200  # nosec B101
    assert medications.json()["data"] == [  # nosec B101
        {
            "id": creation.json()["id"],
            "name": "Lisinopril",
            "dosage": "10 mg",
            "frequency": "Once daily",
        }
    ]


@pytest.mark.django_db
def test_user_cannot_read_another_users_medications():
    first_client, first_token = csrf_client()
    post_json(
        first_client,
        "/api/auth/register/",
        {"email": "first@example.com", "password": TEST_PASSWORD},
        first_token,
    )
    post_json(
        first_client,
        "/api/medications/",
        {"name": "Metformin", "dosage": "500 mg", "frequency": "Twice daily"},
        first_token,
    )

    second_client, second_token = csrf_client()
    post_json(
        second_client,
        "/api/auth/register/",
        {"email": "second@example.com", "password": TEST_PASSWORD},
        second_token,
    )

    medications = get(second_client, "/api/medications/")
    assert medications.status_code == 200  # nosec B101
    assert medications.json()["data"] == []  # nosec B101


@pytest.mark.django_db
def test_private_medication_endpoint_rejects_anonymous_requests():
    response = get(Client(), "/api/medications/")

    assert response.status_code == 401  # nosec B101
    assert response.json()["error"]["code"] == "AUTHENTICATION_REQUIRED"  # nosec B101


@pytest.mark.django_db
@pytest.mark.parametrize("field", ["name", "dosage", "frequency"])
def test_database_rejects_medications_with_blank_required_fields(field: str):
    user = get_user_model().objects.create_user(
        username="patient@example.com",
        email="patient@example.com",
        password=TEST_PASSWORD,
    )
    values = {
        "name": "Lisinopril",
        "dosage": "10 mg",
        "frequency": "Once daily",
    }
    values[field] = ""

    with pytest.raises(IntegrityError):
        with cast(Any, transaction.atomic)():
            cast(Any, Medication).objects.create(
                owner=user,
                **values,
            )
