from functools import wraps

from django.http import JsonResponse
from django.views.decorators.http import require_GET

from .services import get_or_create_schedule, serialize_schedule


def authenticated_api(view):
    @wraps(view)
    def wrapped(request, *args, **kwargs):
        if not request.user.is_authenticated:
            return JsonResponse(
                {"detail": "Authentication credentials were not provided."}, status=401
            )
        return view(request, *args, **kwargs)

    return wrapped


@require_GET
@authenticated_api
def schedule(request):
    medication_schedule = get_or_create_schedule(request.user)
    return JsonResponse({"schedule": serialize_schedule(medication_schedule)})
