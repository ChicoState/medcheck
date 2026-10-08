import json
from typing import Any

import pytest
from django.contrib.auth import get_user_model
from django.contrib.sessions.models import Session
from django.test import Client

pytestmark = pytest.mark.django_db


def payload(**values):
    return json.dumps(values), "application/json"


def csrf_client() -> Any:
    return Client(enforce_csrf_checks=True)


def csrf_token(client):
    return client.get("/api/auth/csrf/").json()["csrfToken"]


def post(client: Client, url: str, data: dict[str, str], token: str) -> Any:
    return client.post(url, *payload(**data), HTTP_X_CSRFTOKEN=token)


def test_registration_persists_hashed_password_and_session():
    client: Any = csrf_client()
    token = csrf_token(client)

    response = post(
        client,
        "/api/auth/register/",
        {"email": "Alice@example.com", "password": "a-strong-password"},
        token,
    )

    assert response.status_code == 201
    user = get_user_model().objects.get(email="alice@example.com")
    assert user.check_password("a-strong-password")
    assert user.password != "a-strong-password"
    assert client.get("/api/auth/session/").json()["authenticated"] is True


def test_duplicate_registration_does_not_replace_password():
    client: Any = csrf_client()
    token = csrf_token(client)
    post(
        client,
        "/api/auth/register/",
        {"email": "alice@example.com", "password": "first-password"},
        token,
    )
    client.post("/api/auth/logout/", HTTP_X_CSRFTOKEN=client.cookies["csrftoken"].value)
    token = client.cookies["csrftoken"].value

    response = post(
        client,
        "/api/auth/register/",
        {"email": "ALICE@example.com", "password": "second-password"},
        token,
    )

    assert response.status_code == 400
    user = get_user_model().objects.get(email="alice@example.com")
    assert user.check_password("first-password")
    assert not user.check_password("second-password")


def test_mutations_require_csrf():
    client: Any = csrf_client()
    response = client.post(
        "/api/auth/register/",
        *payload(email="csrf@example.com", password="a-strong-password"),
    )

    assert response.status_code == 403
    assert not get_user_model().objects.exists()


def test_login_logout_and_invalidated_session():
    user = get_user_model().objects.create_user(
        username="login@example.com",
        email="login@example.com",
        password="a-strong-password",
    )
    client: Any = csrf_client()
    token = csrf_token(client)

    assert (
        post(
            client,
            "/api/auth/login/",
            {"email": user.email, "password": "wrong-password"},
            token,
        ).status_code
        == 400
    )
    assert (
        post(
            client,
            "/api/auth/login/",
            {"email": user.email, "password": "a-strong-password"},
            token,
        ).status_code
        == 200
    )
    session_key = client.cookies["sessionid"].value
    assert Session.objects.filter(session_key=session_key).exists()

    assert (
        client.post(
            "/api/auth/logout/", HTTP_X_CSRFTOKEN=client.cookies["csrftoken"].value
        ).status_code
        == 200
    )
    assert not Session.objects.filter(session_key=session_key).exists()
