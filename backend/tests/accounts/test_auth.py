"""Exercise the public account boundary with real sessions, CSRF and database writes."""

import pytest
from django.contrib.auth.models import User
from django.contrib.sessions.models import Session
from django.core.cache import cache
from django.test import Client

pytestmark = pytest.mark.django_db
PASSWORD = "cedar-otter-lantern-482!"


@pytest.fixture
def browser():
    cache.clear()
    return Client(enforce_csrf_checks=True)


def post(browser, endpoint, data):
    token = browser.get("/api/auth/session/").json()["csrfToken"]
    return browser.post(
        f"/api/auth/{endpoint}/", data, content_type="application/json", HTTP_X_CSRFTOKEN=token
    )


def test_registration_persists_hashed_password_and_restores_session(browser):
    response = post(browser, "register", {"username": "alice", "password": PASSWORD})
    assert response.status_code == 201
    user = User.objects.get(username="alice")
    assert user.check_password(PASSWORD)
    assert user.password != PASSWORD
    assert not user.is_staff and not user.is_superuser
    assert response.json()["user"] == {"id": user.pk, "username": "alice"}
    restored = Client(enforce_csrf_checks=True)
    restored.cookies = browser.cookies.copy()
    # Django test Client dynamically attaches json() to its response.
    restored_response = restored.get("/api/auth/session/")
    assert restored_response.json()["user"] == response.json()["user"]  # pyright: ignore[reportAttributeAccessIssue]
    assert response.headers["Cache-Control"] == "no-store"


def test_duplicate_registration_does_not_replace_password(browser):
    User.objects.create_user(username="alice", password=PASSWORD)
    response = post(browser, "register", {"username": "alice", "password": "different-482!"})
    assert response.status_code == 400
    assert "username" in response.json()["errors"]
    assert User.objects.get(username="alice").check_password(PASSWORD)


@pytest.mark.parametrize("endpoint", ["login", "register", "logout"])
def test_mutations_require_csrf(browser, endpoint):
    response = browser.post(
        f"/api/auth/{endpoint}/",
        {"username": "alice", "password": PASSWORD},
        content_type="application/json",
    )
    assert response.status_code == 403
    assert "__all__" in response.json()["errors"]
    assert User.objects.count() == 0


def test_login_logout_and_invalidated_session(browser):
    user = User.objects.create_user(username="alice", password=PASSWORD)
    response = post(browser, "login", {"username": "alice", "password": PASSWORD})
    assert response.status_code == 200
    assert response.json()["user"] == {"id": user.pk, "username": "alice"}
    session_key = browser.cookies["sessionid"].value
    assert Session.objects.filter(session_key=session_key).exists()
    assert post(browser, "logout", {}).json()["user"] is None
    assert not Session.objects.filter(session_key=session_key).exists()
    assert browser.get("/api/auth/session/").json()["user"] is None


@pytest.mark.parametrize(
    "username,password,active",
    [
        ("missing", PASSWORD, True),
        ("alice", "wrong", True),
        ("alice", PASSWORD, False),
    ],
)
def test_invalid_credentials_are_generic(browser, username, password, active):
    User.objects.create_user(username="alice", password=PASSWORD, is_active=active)
    response = post(browser, "login", {"username": username, "password": password})
    assert response.status_code == 400
    assert response.json() == {"errors": {"__all__": ["Invalid username or password."]}}
    assert browser.get("/api/auth/session/").json()["user"] is None


@pytest.mark.parametrize(
    "data",
    [
        {},
        {"username": "a", "password": "short"},
        {"username": "bad name", "password": PASSWORD},
        {"username": 123, "password": PASSWORD},
        {"username": "alice", "password": [PASSWORD]},
        {"username": "alice", "password": PASSWORD, "is_staff": True},
        {"username": "alice", "password": PASSWORD, "is_superuser": True},
        {"username": "a" * 151, "password": PASSWORD},
        {"username": "alice", "password": "x" * 1025},
        [],
        None,
    ],
)
def test_invalid_registration_rejected(browser, data):
    response = post(browser, "register", data)
    assert response.status_code == 400
    assert response.json()["errors"]
    assert User.objects.count() == 0


def test_malformed_json_rejected(browser):
    assert post(browser, "register", "{broken").status_code == 400


def test_repeated_attempts_are_throttled(browser):
    for _ in range(20):
        assert post(browser, "login", {}).status_code == 400
    response = post(browser, "login", {})
    assert response.status_code == 429
    assert response.headers["Retry-After"] == "60"


def test_registration_race_returns_validation_error():
    from accounts.forms import RegistrationForm

    form = RegistrationForm({"username": "alice", "password": PASSWORD})
    assert form.is_valid()
    User.objects.create_user(username="alice", password=PASSWORD)
    assert form.save() is None
    assert "username" in (form.errors or {})
    assert User.objects.filter(username="alice").count() == 1


def test_csrf_rejects_untrusted_origin_even_with_token(browser):
    token = browser.get("/api/auth/session/").json()["csrfToken"]
    response = browser.post(
        "/api/auth/register/",
        {"username": "alice", "password": PASSWORD},
        content_type="application/json",
        HTTP_X_CSRFTOKEN=token,
        HTTP_ORIGIN="https://untrusted.example",
    )
    assert response.status_code == 403
    assert User.objects.count() == 0


def test_login_rotates_csrf_token(browser):
    User.objects.create_user(username="alice", password=PASSWORD)
    token = browser.get("/api/auth/session/").json()["csrfToken"]
    response = browser.post(
        "/api/auth/login/",
        {"username": "alice", "password": PASSWORD},
        content_type="application/json",
        HTTP_X_CSRFTOKEN=token,
    )
    assert response.status_code == 200
    assert browser.post("/api/auth/logout/", HTTP_X_CSRFTOKEN=token).status_code == 403
    assert (
        browser.post("/api/auth/logout/", HTTP_X_CSRFTOKEN=response.json()["csrfToken"]).status_code
        == 200
    )


@pytest.mark.parametrize("data", [{}, {"username": "alice", "password": 12}, []])
def test_login_validates_credentials(browser, data):
    assert post(browser, "login", data).status_code == 400


def test_get_requests_cannot_mutate_accounts(browser):
    for endpoint in ["login", "register", "logout"]:
        assert browser.get(f"/api/auth/{endpoint}/").status_code == 405
    assert User.objects.count() == 0
