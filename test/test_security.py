"""Security helper tests for wincher_mcp."""

from __future__ import annotations

import httpx
import pytest


class TestValidateApiBaseUrl:
    def test_production_url(self, server_module):
        w = server_module
        assert (
            w._validate_api_base_url("https://api.wincher.com", staging=False)
            == "https://api.wincher.com"
        )

    def test_production_with_trailing_slash(self, server_module):
        w = server_module
        assert (
            w._validate_api_base_url("https://api.wincher.com/", staging=False)
            == "https://api.wincher.com"
        )

    def test_rejects_http(self, server_module):
        w = server_module
        with pytest.raises(ValueError, match="HTTPS"):
            w._validate_api_base_url("http://api.wincher.com", staging=False)

    def test_staging_rejects_localhost(self, server_module):
        w = server_module
        with pytest.raises(ValueError, match="not allowed"):
            w._validate_api_base_url("https://localhost", staging=True)

    def test_staging_rejects_private_ip(self, server_module):
        w = server_module
        with pytest.raises(ValueError, match="not allowed"):
            w._validate_api_base_url("https://10.0.0.1", staging=True)

    def test_staging_rejects_metadata_ip(self, server_module):
        w = server_module
        with pytest.raises(ValueError, match="not allowed"):
            w._validate_api_base_url("https://169.254.169.254", staging=True)

    def test_staging_allows_public_hostname(self, server_module):
        w = server_module
        url = w._validate_api_base_url("https://staging.example.test", staging=True)
        assert url == "https://staging.example.test"


class TestPositiveInt:
    def test_valid(self, server_module):
        w = server_module
        assert w._positive_int("website_id", 42) == 42

    def test_rejects_zero(self, server_module):
        w = server_module
        with pytest.raises(ValueError, match="positive"):
            w._positive_int("website_id", 0)

    def test_rejects_bool(self, server_module):
        w = server_module
        with pytest.raises(ValueError, match="integer"):
            w._positive_int("website_id", True)

    def test_rejects_string(self, server_module):
        w = server_module
        with pytest.raises(ValueError, match="integer"):
            w._positive_int("website_id", "1")


class TestPositiveIntList:
    def test_valid(self, server_module):
        w = server_module
        assert w._positive_int_list("keyword_ids", [1, 2, 3], max_items=10) == [1, 2, 3]

    def test_rejects_over_max(self, server_module):
        w = server_module
        with pytest.raises(ValueError, match="at most"):
            w._positive_int_list("keyword_ids", list(range(11)), max_items=10)

    def test_rejects_non_list(self, server_module):
        w = server_module
        with pytest.raises(ValueError, match="array"):
            w._positive_int_list("keyword_ids", "nope", max_items=10)


class TestFormatRows:
    def test_truncation_notice(self, server_module):
        w = server_module
        items = list(range(w.MAX_FORMAT_ROWS + 10))
        out = w._format_rows(items, lambda n: f"{n}\n", label="items")
        assert f"Showing {w.MAX_FORMAT_ROWS} of" in out
        assert "610" not in out  # item 610 should not appear

    def test_under_limit(self, server_module):
        w = server_module
        out = w._format_rows([1, 2], lambda n: f"{n}\n", label="items")
        assert "Showing" not in out
        assert "1\n2\n" == out


class TestFormatHttpError:
    def test_uses_endpoint_not_request_url(self, server_module):
        w = server_module
        request = httpx.Request("GET", "https://secret-staging.internal/v1/websites")
        response = httpx.Response(401, request=request, text="unauthorized")
        err = httpx.HTTPStatusError("fail", request=request, response=response)
        text = w._format_http_error(err, "/v1/websites")
        assert "secret-staging" not in text
        assert "Endpoint: /v1/websites" in text
        assert "401" in text
