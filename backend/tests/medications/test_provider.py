import json
from email.message import Message
from io import BytesIO
from unittest.mock import patch
from urllib.error import HTTPError, URLError

import pytest

from medications import provider

LABEL_ID = "00653b7c-7099-487e-9a01-e89781c21323"
RECORD = {
    "set_id": LABEL_ID,
    "version": "2",
    "effective_time": "20260429",
    "openfda": {
        "brand_name": [" Ibuprofen Dye Free ", "Ibuprofen Dye Free"],
        "generic_name": ["IBUPROFEN"],
    },
    "warnings": ["Ask a doctor before use.\nStop use if symptoms worsen."],
}


def test_normalization_is_allowlisted_and_stable():
    label = provider.normalize({**RECORD, "untrusted_html": "<script>"}, "2026-10-16")
    assert label is not None
    assert label["externalId"] == LABEL_ID
    assert label["brandNames"] == ["Ibuprofen Dye Free"]
    assert label["sections"] == [
        {
            "key": "warnings",
            "title": "Warnings",
            "text": "Ask a doctor before use.\nStop use if symptoms worsen.",
        }
    ]
    assert "untrusted_html" not in label
    assert provider.normalize({"set_id": "bad"}) is None


@pytest.mark.parametrize("query", ["ibuprofen:other", 'ibuprofen" OR', "foo+bar", "x\\y"])
def test_search_rejects_provider_syntax(query):
    with pytest.raises(ValueError):
        provider._query_term(query)


def test_search_and_detail_pick_valid_label():
    payload = {
        "meta": {"last_updated": "2026-10-16", "results": {"total": 1}},
        "results": [RECORD],
    }
    with patch("medications.provider._fetch", return_value=payload) as fetch:
        labels, total = provider.search_labels("ibuprofen", page=2, page_size=10)
        assert total == 1
        assert labels[0]["displayName"] == "Ibuprofen Dye Free"
        assert fetch.call_args.args[1:] == (10, 10)
        detail = provider.get_label(LABEL_ID)
        assert detail is not None
        assert detail["externalId"] == LABEL_ID


class _Response:
    def __init__(self, body):
        self.body = BytesIO(body)

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return None

    def read(self, count):
        return self.body.read(count)


@pytest.mark.parametrize("body", [b"not json", b"[]", b'{"results":{}}'])
def test_malformed_provider_response_fails_safely(body):
    with patch("medications.provider.build_opener") as opener:
        opener.return_value.open.return_value = _Response(body)
        with pytest.raises(provider.ProviderError) as error:
            provider._fetch("test", 20)
    assert error.value.code == "invalid"


def test_provider_404_is_empty_and_429_is_unavailable():
    with patch("medications.provider.build_opener") as opener:
        opener.return_value.open.side_effect = HTTPError(
            provider.ENDPOINT, 404, "", Message(), None
        )
        assert provider._fetch("test", 20)["results"] == []
        opener.return_value.open.side_effect = HTTPError(
            provider.ENDPOINT, 429, "", Message(), None
        )
        with pytest.raises(provider.ProviderError) as error:
            provider._fetch("test", 20)
        assert error.value.code == "unavailable"
        opener.return_value.open.side_effect = HTTPError(
            provider.ENDPOINT, 302, "", Message(), None
        )
        with pytest.raises(provider.ProviderError) as redirect_error:
            provider._fetch("test", 20)
        assert redirect_error.value.code == "invalid"


def test_network_error_and_oversize_response():
    with patch("medications.provider.build_opener") as opener:
        opener.return_value.open.side_effect = URLError("offline")
        with pytest.raises(provider.ProviderError):
            provider._fetch("test", 20)
        opener.return_value.open.side_effect = None
        opener.return_value.open.return_value = _Response(b"x" * (provider.MAX_RESPONSE_BYTES + 1))
        with pytest.raises(provider.ProviderError) as error:
            provider._fetch("test", 20)
        assert error.value.code == "invalid"


def test_api_key_stays_in_server_authorization_header(monkeypatch):
    monkeypatch.setenv("OPENFDA_API_KEY", "server-only")
    payload = json.dumps({"results": []}).encode()
    with patch("medications.provider.build_opener") as opener:
        opener.return_value.open.return_value = _Response(payload)
        provider._fetch("test", 1)
        request = opener.return_value.open.call_args.args[0]
        assert "server-only" not in request.full_url
        assert request.headers["Authorization"].startswith("Basic ")
