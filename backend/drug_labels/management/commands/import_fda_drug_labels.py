"""Import raw FDA drug-interaction label sections into PostgreSQL."""

import json
import os
from collections.abc import Callable
from typing import Any
from urllib.error import URLError
from urllib.parse import urlencode, urlparse
from urllib.request import Request, urlopen

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from drug_labels.fda import (
    FDA_LABEL_ENDPOINT,
    FDARecordError,
    canonical_source_url,
    parse_label_record,
)
from drug_labels.models import DrugLabelInteraction

PAGE_SIZE = 100
MAX_PAGES = 100
MAX_RESPONSE_BYTES = 5_000_000
REQUEST_TIMEOUT_SECONDS = 10
RETRY_ATTEMPTS = 3

Fetcher = Callable[[str], bytes]


def page_url(offset: int) -> str:
    """Build an allowlisted FDA label request; callers cannot supply a URL."""
    query = {"search": "drug_interactions:*", "limit": PAGE_SIZE, "skip": offset}
    api_key = os.environ.get("FDA_API_KEY")
    if api_key:
        query["api_key"] = api_key
    return f"{FDA_LABEL_ENDPOINT}?{urlencode(query)}"


def fetch_page(url: str) -> bytes:
    """Read one bounded response from the fixed HTTPS FDA endpoint."""
    parsed_url = urlparse(url)
    if parsed_url.scheme != "https" or parsed_url.netloc != "api.fda.gov":
        raise FDARecordError("FDA import URL is outside the allowed endpoint.")

    request = Request(url, headers={"Accept": "application/json"})
    with urlopen(request, timeout=REQUEST_TIMEOUT_SECONDS) as response:  # nosec B310
        body = response.read(MAX_RESPONSE_BYTES + 1)
    if len(body) > MAX_RESPONSE_BYTES:
        raise FDARecordError("FDA response exceeded the configured size limit.")
    return body


def decode_results(body: bytes) -> list[object]:
    try:
        payload: object = json.loads(body)
    except (UnicodeDecodeError, json.JSONDecodeError) as error:
        raise FDARecordError("FDA response was not valid JSON.") from error

    if not isinstance(payload, dict) or not isinstance(payload.get("results"), list):
        raise FDARecordError("FDA response did not contain a results list.")
    return payload["results"]


def save_page(records: list[object]) -> tuple[int, int, int]:
    """Validate a full page before atomically creating or updating its rows."""
    parsed_records = [parse_label_record(record) for record in records]
    created = updated = unchanged = 0

    with transaction.atomic():
        for record in parsed_records:
            defaults: dict[str, Any] = {
                "effective_time": record.effective_time,
                "brand_name": record.brand_name,
                "generic_name": record.generic_name,
                "substance_names": record.substance_names,
                "interaction_text": record.interaction_text,
                "source_url": canonical_source_url(record.set_id),
                "source_hash": record.source_hash,
            }
            label, was_created = DrugLabelInteraction.objects.get_or_create(
                set_id=record.set_id,
                version=record.version,
                defaults=defaults,
            )
            if was_created:
                created += 1
            elif label.source_hash == record.source_hash:
                unchanged += 1
            else:
                for field, value in defaults.items():
                    setattr(label, field, value)
                label.save(update_fields=[*defaults, "imported_at"])
                updated += 1

    return created, updated, unchanged


class Command(BaseCommand):
    help = "Import raw FDA drug-label interaction sections from the fixed openFDA endpoint."

    def add_arguments(self, parser: Any) -> None:
        parser.add_argument(
            "--max-pages",
            default=MAX_PAGES,
            type=int,
            help=f"Maximum FDA pages to import (1-{MAX_PAGES}; default: {MAX_PAGES}).",
        )

    def handle(self, *args: object, **options: Any) -> None:
        max_pages = options["max_pages"]
        if not 1 <= max_pages <= MAX_PAGES:
            raise CommandError(f"--max-pages must be between 1 and {MAX_PAGES}.")

        created = updated = unchanged = 0
        for page in range(max_pages):
            try:
                body = self.fetch_with_retries(page_url(page * PAGE_SIZE))
                results = decode_results(body)
                page_created, page_updated, page_unchanged = save_page(results)
            except (FDARecordError, URLError, TimeoutError, OSError) as error:
                raise CommandError(
                    "FDA import stopped without exposing upstream response content."
                ) from error

            created += page_created
            updated += page_updated
            unchanged += page_unchanged
            if len(results) < PAGE_SIZE:
                break

        self.stdout.write(
            "FDA label import complete: "
            f"created={created}, updated={updated}, unchanged={unchanged}."
        )

    def fetch_with_retries(self, url: str) -> bytes:
        for attempt in range(RETRY_ATTEMPTS):
            try:
                return fetch_page(url)
            except (URLError, TimeoutError, OSError):
                if attempt == RETRY_ATTEMPTS - 1:
                    raise
        raise AssertionError("Retry loop returned without a response or an exception.")
