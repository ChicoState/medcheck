import hashlib
import json
import re
from datetime import date, time, timedelta
from itertools import combinations
from uuid import UUID

from django.core.cache import cache
from django.db import transaction
from django.http import HttpResponse, JsonResponse
from django.utils import timezone
from django.views.decorators.http import require_GET, require_http_methods

from .interactions import check_label_pair
from .models import Medication, MedicationDose, SavedMedication
from .provider import ProviderError, get_label, search_labels, source_url
from .services import get_or_create_schedule, serialize_schedule


@require_GET
def schedule(request):
    if not request.user.is_authenticated:
        return _error("AUTH_REQUIRED", "Sign in to view your medication schedule.", 401)
    user_schedule = get_or_create_schedule(request.user)
    return JsonResponse({"schedule": serialize_schedule(user_schedule)})


@require_http_methods(["PUT", "DELETE"])
def schedule_item(request, saved_id):
    if not request.user.is_authenticated:
        return _error("AUTH_REQUIRED", "Sign in to update your schedule.", 401)
    saved = (
        SavedMedication.objects.filter(pk=saved_id, user=request.user)
        .select_related("medication")
        .first()
    )
    if saved is None:
        return _error("NOT_FOUND", "Saved medication not found.", 404)
    if request.method == "DELETE":
        MedicationDose.objects.filter(saved_medication=saved, schedule__user=request.user).delete()
        return HttpResponse(status=204)
    if len(request.body) > 4096:
        return _error("INVALID_INPUT", "Choose days, a period, and a valid time.", 400)
    try:
        body = json.loads(request.body)
        days = body["days"]
        period = body["period"]
        raw_time = body["time"]
        if (
            not isinstance(raw_time, str)
            or re.fullmatch(r"(?:[01]\d|2[0-3]):[0-5]\d", raw_time) is None
        ):
            raise ValueError("Invalid time")
        dose_time = time.fromisoformat(raw_time)
    except (ValueError, TypeError, KeyError, UnicodeDecodeError, AttributeError):
        return _error("INVALID_INPUT", "Choose days, a period, and a valid time.", 400)
    if (
        not isinstance(days, list)
        or not days
        or len(days) > 7
        or any(type(day) is not int or day not in range(7) for day in days)
        or len(set(days)) != len(days)
        or period not in ("morning", "afternoon", "evening")
        or dose_time.tzinfo is not None
    ):
        return _error("INVALID_INPUT", "Choose days, a period, and a valid time.", 400)
    with transaction.atomic():  # pyright: ignore[reportGeneralTypeIssues]
        user_schedule = get_or_create_schedule(request.user)
        MedicationDose.objects.filter(
            schedule=user_schedule, saved_medication__isnull=True
        ).delete()
        MedicationDose.objects.filter(saved_medication=saved, schedule=user_schedule).delete()
        MedicationDose.objects.bulk_create(
            [
                MedicationDose(
                    schedule=user_schedule,
                    saved_medication=saved,
                    day_of_week=day,
                    medication_name=saved.medication.display_name[:200],
                    time=dose_time,
                    with_food=False,
                    period=period,
                )
                for day in days
            ]
        )
    return JsonResponse(
        {"days": sorted(days), "period": period, "time": dose_time.strftime("%H:%M")}
    )


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


@require_http_methods(["POST"])
def interaction_check(request):
    try:
        content_length = int(request.META.get("CONTENT_LENGTH", "0"))
    except (TypeError, ValueError):
        content_length = 0
    if content_length > 8192:
        return _error("INVALID_INPUT", "Enter two valid medication labels.", 400)
    try:
        body = json.loads(request.body)
    except (json.JSONDecodeError, UnicodeDecodeError):
        return _error("INVALID_INPUT", "Enter two valid medication labels.", 400)
    medications = body.get("medications") if isinstance(body, dict) else None
    if not isinstance(medications, list) or len(medications) != 2:
        return _error("INVALID_INPUT", "Choose exactly two medication labels.", 400)
    parsed = []
    for item in medications:
        if not isinstance(item, dict) or item.get("provider") != "openfda":
            return _error("INVALID_INPUT", "Choose two valid openFDA labels.", 400)
        try:
            external_id = UUID(item.get("externalId"))
        except (TypeError, ValueError, AttributeError):
            return _error("INVALID_INPUT", "Choose two valid openFDA labels.", 400)
        parsed.append(external_id)
    if parsed[0] == parsed[1]:
        return _error("INVALID_INPUT", "Choose two different medication labels.", 400)
    try:
        records = [_medication(external_id) for external_id in parsed]
    except ProviderError as error:
        return _provider_error(error)
    if any(record is None for record in records):
        return _error("NOT_FOUND", "One or more medication labels were not found.", 404)
    first_record, second_record = records
    if first_record is None or second_record is None:
        return _error("NOT_FOUND", "One or more medication labels were not found.", 404)
    labels = [_details(first_record, False), _details(second_record, False)]
    return JsonResponse(check_label_pair(*labels))


@require_GET
def saved_interactions(request):
    if not request.user.is_authenticated:
        return _error("AUTH_REQUIRED", "Sign in to check saved medications.", 401)
    saved = list(
        SavedMedication.objects.filter(user=request.user)
        .select_related("medication")
        .order_by("pk")[:11]
    )
    count = len(saved)
    total_pairs = count * (count - 1) // 2
    if count < 2 or count > 10:
        return JsonResponse(
            {
                "status": "incomplete",
                "pairsChecked": 0,
                "totalPairs": total_pairs,
                "matches": [],
                "reason": "too_many" if count > 10 else "need_two",
            }
        )

    labels = {}
    for item in saved:
        try:
            record = _medication(item.medication.external_id)
        except ProviderError:
            record = None
        if (
            record
            and timezone.now() - record.fetched_at < FRESH_FOR
            and any(
                section.get("key") == "drug_interactions" and section.get("text")
                for section in record.label_sections
            )
        ):
            labels[item.pk] = _details(record, True)

    checked = 0
    matches = []
    for first, second in combinations(saved, 2):
        if first.pk not in labels or second.pk not in labels:
            continue
        checked += 1
        findings = check_label_pair(labels[first.pk], labels[second.pk])["findings"]
        if findings:
            matches.append(
                {
                    "names": [first.medication.display_name, second.medication.display_name],
                    "findings": [
                        {**finding, "text": finding["text"][:600]} for finding in findings
                    ],
                }
            )
    return JsonResponse(
        {
            "status": "match" if matches else "clear" if checked == total_pairs else "incomplete",
            "pairsChecked": checked,
            "totalPairs": total_pairs,
            "matches": matches,
            "reason": "missing_label" if checked != total_pairs else None,
        }
    )


def _schedule_plan(saved):
    doses = list(saved.scheduled_doses.all())
    if not doses:
        return None
    return {
        "days": sorted(dose.day_of_week for dose in doses),
        "period": doses[0].period,
        "time": doses[0].time.strftime("%H:%M"),
    }


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
            .prefetch_related("scheduled_doses")
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
                "schedulePlan": _schedule_plan(item),
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
