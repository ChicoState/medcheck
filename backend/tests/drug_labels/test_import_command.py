"""Tests for the explicit, bounded FDA import command."""

import json

import pytest
from django.core.management import call_command
from django.core.management.base import CommandError

from drug_labels.models import DrugLabelInteraction


def response_for(record: dict[str, object]) -> bytes:
    return json.dumps({"results": [record]}).encode()


def valid_record() -> dict[str, object]:
    return {
        "set_id": "a0000000-0000-0000-0000-000000000001",
        "version": "1",
        "effective_time": "20260101",
        "drug_interactions": ["Avoid combining with example medicine."],
        "openfda": {"substance_name": ["EXAMPLE DRUG"]},
    }


@pytest.mark.django_db
def test_import_is_idempotent_for_an_unchanged_label(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        "drug_labels.management.commands.import_fda_drug_labels.fetch_page",
        lambda url: response_for(valid_record()),
    )

    call_command("import_fda_drug_labels", max_pages=1)
    call_command("import_fda_drug_labels", max_pages=1)

    assert DrugLabelInteraction.objects.count() == 1


@pytest.mark.django_db
def test_invalid_page_does_not_create_a_partial_row(monkeypatch: pytest.MonkeyPatch) -> None:
    record = valid_record()
    record["drug_interactions"] = ["valid", 1]
    monkeypatch.setattr(
        "drug_labels.management.commands.import_fda_drug_labels.fetch_page",
        lambda url: response_for(record),
    )

    with pytest.raises(CommandError, match="FDA import stopped"):
        call_command("import_fda_drug_labels", max_pages=1)

    assert DrugLabelInteraction.objects.count() == 0
