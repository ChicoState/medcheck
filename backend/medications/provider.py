"""Small, server-only adapter for openFDA drug label records."""

import base64
import json
import os
import re
from datetime import datetime
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import HTTPRedirectHandler, Request, build_opener
from uuid import UUID

ENDPOINT = "https://api.fda.gov/drug/label.json"
MAX_RESPONSE_BYTES = 12 * 1024 * 1024
DISCLAIMER = (
    "This is product-label information, not personal medical advice. Labels may differ "
    "from products currently distributed or approved. Ask a healthcare professional "
    "about your medication."
)
SECTIONS = (
    ("purpose", "Purpose"),
    ("indications_and_usage", "Uses and indications"),
    ("warnings", "Warnings"),
    ("boxed_warning", "Boxed warning"),
    ("contraindications", "Contraindications"),
    ("adverse_reactions", "Adverse reactions"),
    ("dosage_and_administration", "Dosage and administration"),
    ("information_for_patients", "Information for patients"),
)


class ProviderError(Exception):
    def __init__(self, code="unavailable"):
        self.code = code
        super().__init__(code)


class _NoRedirect(HTTPRedirectHandler):
    def redirect_request(self, request, fp, code, msg, headers, newurl):
        return None


def _fetch(search, limit, skip=0):
    params = {"search": search, "limit": limit, "skip": skip}
    url = f"{ENDPOINT}?{urlencode(params)}"
    headers = {"Accept": "application/json"}
    key = os.environ.get("OPENFDA_API_KEY", "")
    if key:
        credentials = base64.b64encode(f"{key}:".encode()).decode()
        headers["Authorization"] = f"Basic {credentials}"
    request = Request(url, headers=headers)
    try:
        with build_opener(_NoRedirect).open(request, timeout=5) as response:
            body = response.read(MAX_RESPONSE_BYTES + 1)
    except HTTPError as error:
        if error.code == 404:
            return {"meta": {"results": {"total": 0}}, "results": []}
        if error.code in (429, 500, 502, 503, 504):
            raise ProviderError("unavailable") from error
        raise ProviderError("invalid") from error
    except (URLError, TimeoutError) as error:
        raise ProviderError("unavailable") from error
    if len(body) > MAX_RESPONSE_BYTES:
        raise ProviderError("invalid")
    try:
        data = json.loads(body)
    except (UnicodeDecodeError, json.JSONDecodeError) as error:
        raise ProviderError("invalid") from error
    if not isinstance(data, dict) or not isinstance(data.get("results"), list):
        raise ProviderError("invalid")
    return data


def _strings(value, maximum: int | None = 240, preserve_lines=False):
    if not isinstance(value, list):
        return []
    seen = set()
    result = []
    for item in value:
        if isinstance(item, str):
            cleaned = (
                "\n".join(" ".join(line.split()) for line in item.splitlines()).strip()
                if preserve_lines
                else " ".join(item.split())
            )
            if cleaned and cleaned not in seen:
                seen.add(cleaned)
                result.append(cleaned if maximum is None else cleaned[:maximum])
    return result


def _date(value, format_string):
    if not isinstance(value, str):
        return None
    try:
        return datetime.strptime(value, format_string).date().isoformat()
    except ValueError:
        return None


def source_url(external_id):
    return f"{ENDPOINT}?{urlencode({'search': f'set_id:"{external_id}"'})}"


def normalize(record, dataset_updated_at=None):
    if not isinstance(record, dict):
        return None
    try:
        external_id = str(UUID(record["set_id"]))
    except (KeyError, TypeError, ValueError, AttributeError):
        return None
    annotation = record.get("openfda")
    if not isinstance(annotation, dict):
        annotation = {}
    brands = _strings(annotation.get("brand_name"))
    generics = _strings(annotation.get("generic_name"))
    display_name = next(iter(brands or generics), None)
    if not display_name:
        return None
    sections = []
    for key, title in SECTIONS:
        values = _strings(record.get(key), maximum=None, preserve_lines=True)
        if values:
            sections.append({"key": key, "title": title, "text": "\n\n".join(values)})
    rxcui = _strings(annotation.get("rxcui"), maximum=24)
    return {
        "provider": "openfda",
        "externalId": external_id,
        "displayName": display_name,
        "genericName": generics[0] if generics else None,
        "brandNames": brands,
        "activeIngredients": _strings(record.get("active_ingredient")),
        "dosageForms": _strings(annotation.get("dosage_form")),
        "routes": _strings(annotation.get("route")),
        "rxcui": rxcui[0] if rxcui else None,
        "sections": sections,
        "labelEffectiveDate": _date(record.get("effective_time"), "%Y%m%d"),
        "datasetUpdatedAt": _date(dataset_updated_at, "%Y-%m-%d"),
        "sourceUrl": source_url(external_id),
        "disclaimer": DISCLAIMER,
    }


def _query_term(value):
    if not re.fullmatch(r"[\w\s'.-]+", value, flags=re.UNICODE):
        raise ValueError("Search contains unsupported characters.")
    term = " ".join(value.split()).replace('"', "")
    return f'openfda.brand_name:"{term}" openfda.generic_name:"{term}"'


def search_labels(query, *, page, page_size):
    data = _fetch(_query_term(query), page_size, (page - 1) * page_size)
    meta = data.get("meta")
    if not isinstance(meta, dict):
        raise ProviderError("invalid")
    metadata = meta.get("results")
    if not isinstance(metadata, dict):
        raise ProviderError("invalid")
    total = metadata.get("total")
    if isinstance(total, bool) or not isinstance(total, int) or total < 0:
        raise ProviderError("invalid")
    updated = meta.get("last_updated")
    labels = [normalize(record, updated) for record in data["results"]]
    return [label for label in labels if label], total


def get_label(external_id):
    data = _fetch(f'set_id:"{external_id}"', 20)
    meta = data.get("meta")
    if not isinstance(meta, dict):
        raise ProviderError("invalid")
    updated = meta.get("last_updated")
    matches = [
        (record, normalize(record, updated))
        for record in data["results"]
        if isinstance(record, dict) and record.get("set_id") == external_id
    ]
    matches = [(record, label) for record, label in matches if label]
    if not matches:
        return None
    record, label = max(
        matches,
        key=lambda pair: (
            int(pair[0].get("version", "0")) if str(pair[0].get("version", "0")).isdigit() else 0,
            str(pair[0].get("effective_time", "")),
        ),
    )
    return label
