"""Validation and provenance helpers for FDA drug-label API records."""

import hashlib
import json
from dataclasses import dataclass
from typing import Any
from urllib.parse import urlencode

FDA_LABEL_ENDPOINT = "https://api.fda.gov/drug/label.json"
MAX_INTERACTION_TEXT_LENGTH = 1_000_000


class FDARecordError(ValueError):
    """Raised when an FDA label record cannot be safely persisted."""


@dataclass(frozen=True)
class ParsedLabelRecord:
    set_id: str
    version: str
    effective_time: str
    brand_name: str
    generic_name: str
    substance_names: list[str]
    interaction_text: str
    source_hash: str


def parse_label_record(record: object) -> ParsedLabelRecord:
    """Validate one openFDA label result without inferring interaction pairs."""
    if not isinstance(record, dict):
        raise FDARecordError("FDA record must be an object.")

    set_id = required_string(record, "set_id")
    version = required_string(record, "version")
    effective_time = optional_string(record, "effective_time")
    interaction_text = interaction_text_from(record.get("drug_interactions"))

    openfda = record.get("openfda", {})
    if not isinstance(openfda, dict):
        raise FDARecordError("FDA openfda metadata must be an object.")

    brand_name = first_string(openfda, "brand_name")
    generic_name = first_string(openfda, "generic_name")
    substance_names = string_list(openfda, "substance_name")
    normalized_payload = {
        "brand_name": brand_name,
        "effective_time": effective_time,
        "generic_name": generic_name,
        "interaction_text": interaction_text,
        "set_id": set_id,
        "substance_names": substance_names,
        "version": version,
    }
    payload = json.dumps(
        normalized_payload, ensure_ascii=True, separators=(",", ":"), sort_keys=True
    )

    return ParsedLabelRecord(
        set_id=set_id,
        version=version,
        effective_time=effective_time,
        brand_name=brand_name,
        generic_name=generic_name,
        substance_names=substance_names,
        interaction_text=interaction_text,
        source_hash=hashlib.sha256(payload.encode()).hexdigest(),
    )


def canonical_source_url(set_id: str) -> str:
    """Return the fixed-endpoint URL that identifies one label set."""
    return f"{FDA_LABEL_ENDPOINT}?{urlencode({'search': f'set_id:{set_id}', 'limit': 1})}"


def required_string(record: dict[str, Any], field: str) -> str:
    value = record.get(field)
    if not isinstance(value, str) or not value.strip():
        raise FDARecordError(f"FDA record has no valid {field}.")
    return value


def optional_string(record: dict[str, Any], field: str) -> str:
    value = record.get(field, "")
    if value is None:
        return ""
    if not isinstance(value, str):
        raise FDARecordError(f"FDA record has invalid {field}.")
    return value


def string_list(record: dict[str, Any], field: str) -> list[str]:
    value = record.get(field, [])
    if not isinstance(value, list) or not all(isinstance(item, str) and item for item in value):
        raise FDARecordError(f"FDA record has invalid {field}.")
    return value


def first_string(record: dict[str, Any], field: str) -> str:
    values = string_list(record, field)
    return values[0] if values else ""


def interaction_text_from(value: object) -> str:
    if not isinstance(value, list) or not all(isinstance(item, str) for item in value):
        raise FDARecordError("FDA record has invalid drug_interactions.")

    text = "\n\n".join(value)
    if not text.strip() or len(text) > MAX_INTERACTION_TEXT_LENGTH:
        raise FDARecordError("FDA record has invalid drug_interactions.")
    return text
