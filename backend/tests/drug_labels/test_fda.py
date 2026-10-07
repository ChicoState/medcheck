"""Pure FDA payload parsing tests."""

import pytest

from drug_labels.fda import FDARecordError, parse_label_record


def valid_record() -> dict[str, object]:
    return {
        "set_id": "a0000000-0000-0000-0000-000000000001",
        "version": "7",
        "effective_time": "20260101",
        "drug_interactions": ["Avoid combining with example medicine."],
        "openfda": {
            "brand_name": ["Example Brand"],
            "generic_name": ["example drug"],
            "substance_name": ["EXAMPLE DRUG"],
        },
    }


def test_parses_source_fields_and_hashes_normalized_payload() -> None:
    record = valid_record()

    parsed = parse_label_record(record)

    assert parsed.set_id == record["set_id"]
    assert parsed.version == record["version"]
    assert parsed.interaction_text == "Avoid combining with example medicine."
    assert parsed.substance_names == ["EXAMPLE DRUG"]
    assert len(parsed.source_hash) == 64


@pytest.mark.parametrize(
    "field, value",
    [
        ("set_id", ""),
        ("version", None),
        ("drug_interactions", ["   "]),
        ("drug_interactions", "not a list"),
    ],
)
def test_rejects_malformed_required_source_data(field: str, value: object) -> None:
    record = valid_record()
    record[field] = value

    with pytest.raises(FDARecordError):
        parse_label_record(record)
