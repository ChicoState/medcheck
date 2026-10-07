"""Thin HTTP controllers; Django owns passwords, account constraints and sessions."""

import hashlib
import json

from django.contrib.auth import authenticate, login, logout
from django.core.cache import cache
from django.http import HttpRequest, JsonResponse
from django.middleware.csrf import get_token
from django.views import View

from accounts.forms import CredentialsForm, RegistrationForm


def error_response(message: str, status: int = 400) -> JsonResponse:
    return JsonResponse({"errors": {"__all__": [message]}}, status=status)


def csrf_failure(request: HttpRequest, reason: str = "") -> JsonResponse:
    return error_response("Your session security token expired. Refresh and try again.", 403)


def session_response(request: HttpRequest, status: int = 200) -> JsonResponse:
    # AuthenticationMiddleware attaches user dynamically.
    user = request.user  # pyright: ignore[reportAttributeAccessIssue]
    response = JsonResponse(
        {
            "user": {"id": user.pk, "username": user.username} if user.is_authenticated else None,
            "csrfToken": get_token(request),
        },
        status=status,
    )
    response["Cache-Control"] = "no-store"
    return response


def credentials(request: HttpRequest) -> dict[str, str] | JsonResponse:
    if request.content_type != "application/json" or len(request.body) > 8192:
        return error_response("Send a small JSON object containing username and password.")
    try:
        data = json.loads(request.body)
    except (ValueError, UnicodeDecodeError):
        return error_response("Invalid JSON.")
    if (
        not isinstance(data, dict)
        or set(data) - {"username", "password"}
        or any(not isinstance(value, str) for value in data.values())
    ):
        return error_response("Only username and password text fields are accepted.")
    return data


def throttled(request: HttpRequest) -> bool:
    # Local cache is per process. Configure shared cache/edge limits before deployment.
    # Do not trust client-supplied forwarding headers.
    address = request.META.get("REMOTE_ADDR", "unknown")
    key = "account-attempts:" + hashlib.sha256(address.encode()).hexdigest()
    if cache.add(key, 1, timeout=60):
        return False
    try:
        return cache.incr(key) > 20
    except ValueError:  # The key expired between add and incr.
        cache.add(key, 1, timeout=60)
        return False


class SessionView(View):
    http_method_names = ["get"]

    def get(self, request: HttpRequest) -> JsonResponse:
        return session_response(request)


class CredentialsView(View):
    http_method_names = ["post"]
    form_class = CredentialsForm

    def post(self, request: HttpRequest) -> JsonResponse:
        if throttled(request):
            response = error_response("Too many attempts. Try again in a minute.", 429)
            response["Retry-After"] = "60"
            return response
        data = credentials(request)
        if isinstance(data, JsonResponse):
            return data
        form = self.form_class(data)
        if not form.is_valid():
            return JsonResponse({"errors": dict(form.errors or {})}, status=400)
        return self.submit(request, form)

    def submit(self, request: HttpRequest, form: CredentialsForm) -> JsonResponse:
        user = authenticate(request, **form.cleaned_data)
        if user is None:
            return error_response("Invalid username or password.")
        login(request, user)
        return session_response(request)


class RegisterView(CredentialsView):
    form_class = RegistrationForm

    def submit(self, request: HttpRequest, form: CredentialsForm) -> JsonResponse:
        if not isinstance(form, RegistrationForm):
            raise TypeError("Registration requires a registration form.")
        user = form.save()
        if user is None:
            return JsonResponse({"errors": dict(form.errors or {})}, status=400)
        login(request, user, backend="django.contrib.auth.backends.ModelBackend")
        return session_response(request, status=201)


class LogoutView(View):
    http_method_names = ["post"]

    def post(self, request: HttpRequest) -> JsonResponse:
        logout(request)
        return session_response(request)
