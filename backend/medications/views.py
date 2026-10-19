import hashlib
import json
from functools import wraps

from django.contrib.auth import authenticate, get_user_model, login, logout
from django.contrib.auth.password_validation import validate_password
from django.core.cache import cache
from django.core.exceptions import ValidationError
from django.core.validators import validate_email
from django.db import IntegrityError, transaction
from django.http import HttpRequest, HttpResponse, JsonResponse
from django.middleware.csrf import get_token
from django.views.decorators.csrf import ensure_csrf_cookie
from django.views.decorators.http import require_GET, require_http_methods, require_POST

from .models import Medication

MAX_LOGIN_ATTEMPTS = 10
LOGIN_WINDOW_SECONDS = 15 * 60
MEDICATION_FIELDS = ("name", "dosage", "frequency")


def error(code: str, message: str, status: int) -> JsonResponse:
    return JsonResponse({"error": {"code": code, "message": message}}, status=status)


def json_body(request: HttpRequest) -> dict[str, str] | None:
    try:
        payload = json.loads(request.body)
    except (json.JSONDecodeError, UnicodeDecodeError):
        return None
    if not isinstance(payload, dict) or not all(
        isinstance(value, str) for value in payload.values()
    ):
        return None
    return payload


def user_data(user) -> dict[str, int | str]:
    return {"id": user.id, "email": user.email}


def medication_data(medication: Medication) -> dict[str, int | str]:
    return {
        "id": medication.id,
        "name": medication.name,
        "dosage": medication.dosage,
        "frequency": medication.frequency,
    }


def api_login_required(view):
    @wraps(view)
    def wrapped(request: HttpRequest, *args, **kwargs):
        if not request.user.is_authenticated:
            return error("AUTHENTICATION_REQUIRED", "Sign in to continue.", 401)
        return view(request, *args, **kwargs)

    return wrapped


def login_rate_limited(request: HttpRequest) -> bool:
    client_ip = request.META.get("REMOTE_ADDR", "unknown")
    key = f"login-attempts:{hashlib.sha256(client_ip.encode()).hexdigest()}"
    attempts = cache.get(key, 0)
    if attempts >= MAX_LOGIN_ATTEMPTS:
        return True
    cache.add(key, 0, LOGIN_WINDOW_SECONDS)
    return False


def record_failed_login(request: HttpRequest) -> None:
    client_ip = request.META.get("REMOTE_ADDR", "unknown")
    key = f"login-attempts:{hashlib.sha256(client_ip.encode()).hexdigest()}"
    cache.add(key, 0, LOGIN_WINDOW_SECONDS)
    cache.incr(key)


@require_GET
@ensure_csrf_cookie
def csrf_token(request: HttpRequest) -> JsonResponse:
    return JsonResponse({"csrfToken": get_token(request)})


@require_POST
def register(request: HttpRequest) -> JsonResponse:
    payload = json_body(request)
    if payload is None:
        return error("VALIDATION_ERROR", "Submit a JSON object.", 400)

    email = payload.get("email", "").strip().lower()
    password = payload.get("password", "")
    try:
        validate_email(email)
        validate_password(password)
    except ValidationError:
        return error("VALIDATION_ERROR", "Enter a valid email and stronger password.", 400)

    try:
        with transaction.atomic():
            user = get_user_model().objects.create_user(
                username=email,
                email=email,
                password=password,
            )
    except IntegrityError:
        return error("EMAIL_UNAVAILABLE", "That email is already registered.", 409)

    login(request, user)
    return JsonResponse({"user": user_data(user)}, status=201)


@require_POST
def login_view(request: HttpRequest) -> JsonResponse:
    if login_rate_limited(request):
        return error("RATE_LIMITED", "Try again later.", 429)

    payload = json_body(request)
    if payload is None:
        return error("VALIDATION_ERROR", "Submit a JSON object.", 400)

    email = payload.get("email", "").strip().lower()
    password = payload.get("password", "")
    user = authenticate(request, username=email, password=password)
    if user is None:
        record_failed_login(request)
        return error("INVALID_CREDENTIALS", "Email or password is incorrect.", 401)

    login(request, user)
    return JsonResponse({"user": user_data(user)})


@require_POST
@api_login_required
def logout_view(request: HttpRequest) -> HttpResponse:
    logout(request)
    return HttpResponse(status=204)


@require_GET
@api_login_required
def current_user(request: HttpRequest) -> JsonResponse:
    return JsonResponse({"user": user_data(request.user)})


@require_http_methods(["GET", "POST"])
@api_login_required
def medications(request: HttpRequest) -> JsonResponse:
    if request.method == "GET":
        records = Medication.objects.filter(owner=request.user)
        return JsonResponse({"data": [medication_data(record) for record in records]})

    payload = json_body(request)
    if payload is None:
        return error("VALIDATION_ERROR", "Submit a JSON object.", 400)

    values = {field: payload.get(field, "").strip() for field in MEDICATION_FIELDS}
    if any(not value or len(value) > 120 for value in values.values()):
        return error("VALIDATION_ERROR", "Name, dosage, and frequency are required.", 400)

    medication = Medication.objects.create(owner=request.user, **values)
    return JsonResponse(medication_data(medication), status=201)
