import json

from django.contrib.auth import authenticate, get_user_model, login, logout
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError
from django.http import JsonResponse
from django.middleware.csrf import get_token
from django.views.decorators.http import require_GET, require_POST

REQUIRED_CREDENTIAL_MESSAGE = "Enter a password."
MISMATCH_CREDENTIAL_MESSAGE = "Passwords do not match."


def _json_body(request):
    try:
        body = json.loads(request.body or "{}")
    except json.JSONDecodeError:
        return None
    return body if isinstance(body, dict) else None


def _errors(**errors):
    return JsonResponse({"errors": errors}, status=400)


def _user_data(user):
    return {"id": user.pk, "username": user.username, "email": user.email}


@require_GET
def csrf(request):
    return JsonResponse({"csrfToken": get_token(request)})


@require_POST
def register(request):
    data = _json_body(request)
    if data is None:
        return _errors(form="Request body must be a JSON object.")

    email = str(data.get("email", "")).strip().lower()
    username = str(data.get("username", email)).strip()
    password = data.get("password", "")
    confirmation = data.get("password_confirmation")
    errors = {}
    if not email or "@" not in email:
        errors["email"] = "Enter a valid email address."
    if not username:
        errors["username"] = "Enter a username."
    if not isinstance(password, str) or not password:
        errors["password"] = REQUIRED_CREDENTIAL_MESSAGE
    elif confirmation is not None and password != confirmation:
        errors["password_confirmation"] = MISMATCH_CREDENTIAL_MESSAGE
    if errors:
        return _errors(**errors)

    User = get_user_model()
    if (
        User.objects.filter(email__iexact=email).exists()
        or User.objects.filter(username__iexact=username).exists()
    ):
        return _errors(email="Unable to register with this email address.")
    user = User(username=username, email=email)
    try:
        validate_password(password, user)
    except ValidationError as error:
        return _errors(password=list(error.messages))
    user.set_password(password)
    user.save()
    login(request, user)
    return JsonResponse({"user": _user_data(user)}, status=201)


@require_POST
def login_view(request):
    data = _json_body(request)
    if data is None:
        return _errors(form="Request body must be a JSON object.")
    email = str(data.get("email", data.get("username", ""))).strip().lower()
    password = data.get("password", "")
    user = authenticate(request, username=data.get("username", email), password=password)
    if user is None:
        return _errors(form="Unable to sign in with those credentials.")
    login(request, user)
    return JsonResponse({"user": _user_data(user)})


@require_POST
def logout_view(request):
    logout(request)
    return JsonResponse({"ok": True})


@require_GET
def me(request):
    if not request.user.is_authenticated:
        return JsonResponse({"authenticated": False}, status=401)
    return JsonResponse({"user": _user_data(request.user)})


@require_GET
def session(request):
    if not request.user.is_authenticated:
        return JsonResponse({"authenticated": False}, status=401)
    return JsonResponse({"authenticated": True, "user": _user_data(request.user)})
