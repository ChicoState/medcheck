"""Safety boundaries for FDA import transport."""

import pytest

from drug_labels.fda import FDARecordError
from drug_labels.management.commands.import_fda_drug_labels import fetch_page


def test_rejects_a_non_fda_import_url_without_requesting_it() -> None:
    with pytest.raises(FDARecordError, match="outside the allowed endpoint"):
        fetch_page("https://example.test/not-fda")
