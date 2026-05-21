"""Security helper tests for wincher_mcp_server."""

from __future__ import annotations

import importlib.util
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
SERVER_PATH = REPO_ROOT / "wincher_mcp_server.py"


def load_server_module():
    spec = importlib.util.spec_from_file_location("wincher_mcp_server", SERVER_PATH)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


@pytest.fixture(scope="module")
def w():
    return load_server_module()


class TestValidateApiBaseUrl:
    def test_production_url(self, w):
        assert (
            w._validate_api_base_url("https://api.wincher.com", staging=False)
            == "https://api.wincher.com"
        )

    def test_production_with_trailing_slash(self, w):
        assert (
            w._validate_api_base_url("https://api.wincher.com/", staging=False)
            == "https://api.wincher.com"
        )

    def test_rejects_http(self, w):
        with pytest.raises(ValueError, match="HTTPS"):
            w._validate_api_base_url("http://api.wincher.com", staging=False)

    def test_staging_rejects_localhost(self, w):
        with pytest.raises(ValueError, match="not allowed"):
            w._validate_api_base_url("https://localhost", staging=True)

    def test_staging_rejects_private_ip(self, w):
        with pytest.raises(ValueError, match="not allowed"):
            w._validate_api_base_url("https://10.0.0.1", staging=True)

    def test_staging_rejects_metadata_ip(self, w):
        with pytest.raises(ValueError, match="not allowed"):
            w._validate_api_base_url("https://169.254.169.254", staging=True)

    def test_staging_allows_public_hostname(self, w):
        url = w._validate_api_base_url("https://staging.example.test", staging=True)
        assert url == "https://staging.example.test"


class TestPositiveInt:
    def test_valid(self, w):
        assert w._positive_int("website_id", 42) == 42

    def test_rejects_zero(self, w):
        with pytest.raises(ValueError, match="positive"):
            w._positive_int("website_id", 0)

    def test_rejects_bool(self, w):
        with pytest.raises(ValueError, match="integer"):
            w._positive_int("website_id", True)

    def test_rejects_string(self, w):
        with pytest.raises(ValueError, match="integer"):
            w._positive_int("website_id", "1")


class TestPositiveIntList:
    def test_valid(self, w):
        assert w._positive_int_list("keyword_ids", [1, 2, 3], max_items=10) == [1, 2, 3]

    def test_rejects_over_max(self, w):
        with pytest.raises(ValueError, match="at most"):
            w._positive_int_list("keyword_ids", list(range(11)), max_items=10)

    def test_rejects_non_list(self, w):
        with pytest.raises(ValueError, match="array"):
            w._positive_int_list("keyword_ids", "nope", max_items=10)


class TestFormatRows:
    def test_truncation_notice(self, w):
        items = list(range(w.MAX_FORMAT_ROWS + 10))
        out = w._format_rows(items, lambda n: f"{n}\n", label="items")
        assert f"Showing {w.MAX_FORMAT_ROWS} of" in out
        assert "610" not in out  # item 610 should not appear

    def test_under_limit(self, w):
        out = w._format_rows([1, 2], lambda n: f"{n}\n", label="items")
        assert "Showing" not in out
        assert "1\n2\n" == out


class TestFormatHttpError:
    def test_uses_endpoint_not_request_url(self, w):
        import httpx

        request = httpx.Request("GET", "https://secret-staging.internal/v1/websites")
        response = httpx.Response(401, request=request, text="unauthorized")
        err = httpx.HTTPStatusError("fail", request=request, response=response)
        text = w._format_http_error(err, "/v1/websites")
        assert "secret-staging" not in text
        assert "Endpoint: /v1/websites" in text
        assert "401" in text
