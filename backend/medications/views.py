import hashlib
import json
from datetime import date, timedelta
from uuid import UUID

from django.core.cache import cache
from django.http import HttpResponse, JsonResponse
from django.utils import timezone
from django.views.decorators.http import require_GET, require_http_methods

from .models import Medication, SavedMedication
from .provider import ProviderError, get_label, search_labels, source_url

FRESH_FOR = timedelta(hours=24)


def _error(code, message, status):
    return JsonResponse({"error": {"code": code, "message": message}}, status=status)


def _provider_error(error):
    if error.code == "invalid":
        return _error("INVALID_PROVIDER_RESPONSE", "Drug information is unavailable.", 502)
    return _error("PROVIDER_UNAVAILABLE", "Drug information is temporarily unavailable.", 503)


def _page(request):
    try:
        page = int(request.GET.get("page", "1"))
        size = int(request.GET.get("pageSize", "20"))
    except ValueError:
        return None
    if page < 1 or not 1 <= size <= 20 or (page - 1) * size > 25000:
        return None
    return page, size


def _pagination(page, size, total):
    return {
        "page": page,
        "pageSize": size,
        "hasNextPage": page * size < total and page * size <= 25000,
    }


def _summary(medication):
    return {
        "provider": medication.provider,
        "externalId": str(medication.external_id),
        "displayName": medication.display_name,
        "genericName": medication.generic_name,
        "brandNames": medication.brand_names,
        "activeIngredients": medication.active_ingredients,
        "dosageForms": medication.dosage_forms,
        "routes": medication.routes,
        "rxcui": medication.rxcui,
    }


def _details(medication, is_saved):
    return {
        **_summary(medication),
        "sections": medication.label_sections,
        "labelEffectiveDate": medication.label_effective_date.isoformat()
        if medication.label_effective_date
        else None,
        "datasetUpdatedAt": medication.dataset_updated_at.isoformat()
        if medication.dataset_updated_at
        else None,
        "fetchedAt": medication.fetched_at.isoformat(),
        "isStale": timezone.now() - medication.fetched_at >= FRESH_FOR,
        "sourceUrl": source_url(str(medication.external_id)),
        "disclaimer": (
            "This is product-label information, not personal medical advice. Labels may differ "
            "from products currently distributed or approved. Ask a healthcare professional "
            "about your medication."
        ),
        "isSaved": is_saved,
    }


def _save_label(label):
    fields = {
        "display_name": label["displayName"],
        "generic_name": label["genericName"],
        "brand_names": label["brandNames"],
        "active_ingredients": label["activeIngredients"],
        "dosage_forms": label["dosageForms"],
        "routes": label["routes"],
        "rxcui": label["rxcui"],
        "label_sections": label["sections"],
        "label_effective_date": date.fromisoformat(label["labelEffectiveDate"])
        if label["labelEffectiveDate"]
        else None,
        "dataset_updated_at": date.fromisoformat(label["datasetUpdatedAt"])
        if label["datasetUpdatedAt"]
        else None,
        "fetched_at": timezone.now(),
    }
    medication, _ = Medication.objects.update_or_create(
        provider="openfda", external_id=label["externalId"], defaults=fields
    )
    return medication


def _medication(external_id):
    existing = Medication.objects.filter(provider="openfda", external_id=external_id).first()
    if existing and timezone.now() - existing.fetched_at < FRESH_FOR:
        return existing
    try:
        label = get_label(str(external_id))
    except ProviderError:
        if existing:
            return existing
        raise
    if label is None:
        return existing
    return _save_label(label)


@require_GET
def search(request):
    parsed = _page(request)
    query = " ".join(request.GET.get("q", "").split())
    if parsed is None or not 1 <= len(query) <= 100:
        return _error("INVALID_QUERY", "Enter a medication name and valid page.", 400)
    page, size = parsed
    identity = (
        request.user.pk if request.user.is_authenticated else request.META.get("REMOTE_ADDR", "")
    )
    throttle_key = "medication-throttle:" + hashlib.sha256(str(identity).encode()).hexdigest()
    cache.add(throttle_key, 0, 60)
    if cache.incr(throttle_key) > 60:
        return _error("RATE_LIMITED", "Too many searches. Please try again shortly.", 429)
    cache_key = (
        "medication-search:"
        + hashlib.sha256(f"{query.casefold()}:{page}:{size}".encode()).hexdigest()
    )
    cached = cache.get(cache_key)
    if cached is None:
        try:
            labels, total = search_labels(query, page=page, page_size=size)
        except ValueError:
            return _error("INVALID_QUERY", "Search contains unsupported characters.", 400)
        except ProviderError as error:
            return _provider_error(error)
        cache.set(cache_key, (labels, total), 300)
    else:
        labels, total = cached
    saved_ids = set()
    if request.user.is_authenticated and labels:
        saved_ids = set(
            SavedMedication.objects.filter(
                user=request.user, medication__external_id__in=[x["externalId"] for x in labels]
            ).values_list("medication__external_id", flat=True)
        )
    fields = (
        "provider",
        "externalId",
        "displayName",
        "genericName",
        "brandNames",
        "activeIngredients",
        "dosageForms",
        "routes",
        "rxcui",
    )
    data = [
        {**{key: label[key] for key in fields}, "isSaved": UUID(label["externalId"]) in saved_ids}
        for label in labels
    ]
    return JsonResponse({"data": data, "pagination": _pagination(page, size, total)})


@require_GET
def detail(request, provider, external_id):
    if provider != "openfda":
        return _error("NOT_FOUND", "Medication label not found.", 404)
    try:
        medication = _medication(external_id)
    except ProviderError as error:
        return _provider_error(error)
    if medication is None:
        return _error("NOT_FOUND", "Medication label not found.", 404)
    saved = (
        request.user.is_authenticated
        and SavedMedication.objects.filter(user=request.user, medication=medication).exists()
    )
    return JsonResponse(_details(medication, saved))


@require_http_methods(["GET", "POST"])
def saved_collection(request):
    if not request.user.is_authenticated:
        return _error("AUTH_REQUIRED", "Sign in to view saved medications.", 401)
    if request.method == "GET":
        parsed = _page(request)
        if parsed is None:
            return _error("INVALID_PAGE", "Enter a valid page.", 400)
        page, size = parsed
        records = (
            SavedMedication.objects.filter(user=request.user)
            .select_related("medication")
            .order_by("-saved_at", "-pk")
        )
        total = records.count()
        data = [
            {
                **_summary(item.medication),
                "savedId": item.pk,
                "savedAt": item.saved_at.isoformat(),
                "labelEffectiveDate": item.medication.label_effective_date.isoformat()
                if item.medication.label_effective_date
                else None,
                "fetchedAt": item.medication.fetched_at.isoformat(),
                "isStale": timezone.now() - item.medication.fetched_at >= FRESH_FOR,
            }
            for item in records[(page - 1) * size : page * size]
        ]
        return JsonResponse({"data": data, "pagination": _pagination(page, size, total)})
    try:
        body = json.loads(request.body)
    except (json.JSONDecodeError, UnicodeDecodeError):
        return _error("INVALID_INPUT", "Enter a valid medication label.", 400)
    if not isinstance(body, dict) or body.get("provider") != "openfda":
        return _error("INVALID_INPUT", "Enter a valid medication label.", 400)
    try:
        external_id = UUID(body.get("externalId"))
    except (TypeError, ValueError, AttributeError):
        return _error("INVALID_INPUT", "Enter a valid medication label.", 400)
    try:
        medication = _medication(external_id)
    except ProviderError as error:
        return _provider_error(error)
    if medication is None:
        return _error("NOT_FOUND", "Medication label not found.", 404)
    saved, created = SavedMedication.objects.get_or_create(user=request.user, medication=medication)
    return JsonResponse({"savedId": saved.pk, "created": created}, status=201 if created else 200)


@require_http_methods(["DELETE"])
def saved_item(request, saved_id):
    if not request.user.is_authenticated:
        return _error("AUTH_REQUIRED", "Sign in to update saved medications.", 401)
    deleted, _ = SavedMedication.objects.filter(pk=saved_id, user=request.user).delete()
    if not deleted:
        return _error("NOT_FOUND", "Saved medication not found.", 404)
    return HttpResponse(status=204)
