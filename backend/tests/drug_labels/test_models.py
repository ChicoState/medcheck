"""Database behavior for FDA label interaction provenance."""

import pytest
from django.db import IntegrityError

from drug_labels.models import DrugLabelInteraction


@pytest.mark.django_db
def test_rejects_duplicate_label_versions() -> None:
    values = {
        "set_id": "a0000000-0000-0000-0000-000000000001",
        "version": "1",
        "effective_time": "20260101",
        "brand_name": "Example Brand",
        "generic_name": "example drug",
        "substance_names": ["EXAMPLE DRUG"],
        "interaction_text": "Example interaction text.",
        "source_url": "https://api.fda.gov/drug/label.json?search=set_id:example",
        "source_hash": "a" * 64,
    }

    DrugLabelInteraction.objects.create(**values)

    with pytest.raises(IntegrityError):
        DrugLabelInteraction.objects.create(**values)
