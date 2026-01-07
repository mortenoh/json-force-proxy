"""Tests for the proxy server."""

from collections.abc import Generator
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi.testclient import TestClient
from httpx import RequestError, TimeoutException
from httpx import Response as HttpxResponse

from json_force_proxy.server import app
from json_force_proxy.settings import LogLevel, Settings, get_settings


@pytest.fixture
def client() -> TestClient:
    """Create a test client."""
    return TestClient(app)


@pytest.fixture(autouse=True)
def reset_settings_cache() -> Generator[None, None, None]:
    """Reset settings cache and set default target URL for tests."""
    import os

    os.environ["JSON_FORCE_PROXY_TARGET_URL"] = "https://api.example.com"
    get_settings.cache_clear()
    yield
    os.environ.pop("JSON_FORCE_PROXY_TARGET_URL", None)
    get_settings.cache_clear()


@pytest.fixture
def mock_httpx_client() -> Generator[MagicMock, None, None]:
    """Create a mock httpx client."""
    with patch("json_force_proxy.server.httpx.AsyncClient") as mock_client:
        mock_instance = AsyncMock()
        mock_instance.__aenter__.return_value = mock_instance
        mock_instance.__aexit__.return_value = None
        mock_client.return_value = mock_instance
        yield mock_instance


def make_response(
    status_code: int = 200,
    content: bytes = b"{}",
    headers: dict[str, str] | None = None,
) -> HttpxResponse:
    """Create an httpx Response with proper headers."""
    return HttpxResponse(status_code, content=content, headers=headers or {})


class TestProxyEndpoints:
    """Tests for proxy endpoints."""

    def test_successful_proxy_returns_json_content_type(self, client: TestClient, mock_httpx_client: MagicMock) -> None:
        """Test that successful responses have application/json Content-Type."""
        mock_httpx_client.request.return_value = make_response(200, b'{"key": "value"}')

        response = client.get("/")

        assert response.status_code == 200
        assert response.headers["content-type"] == "application/json"
        assert response.content == b'{"key": "value"}'

    def test_upstream_error_returns_502(self, client: TestClient, mock_httpx_client: MagicMock) -> None:
        """Test that upstream errors return 502 status."""
        mock_httpx_client.request.side_effect = RequestError("Connection refused")

        response = client.get("/")

        assert response.status_code == 502
        assert response.headers["content-type"] == "text/plain; charset=utf-8"
        assert b"Error fetching upstream" in response.content

    def test_proxy_root_path(self, client: TestClient, mock_httpx_client: MagicMock) -> None:
        """Test that root path proxies correctly."""
        mock_httpx_client.request.return_value = make_response(200, b'{"root": true}')

        response = client.get("/")

        assert response.status_code == 200
        assert response.json() == {"root": True}

    def test_proxy_nested_path(self, client: TestClient, mock_httpx_client: MagicMock) -> None:
        """Test that nested paths are proxied."""
        mock_httpx_client.request.return_value = make_response(200, b'{"path": "nested"}')

        response = client.get("/some/nested/path")

        assert response.status_code == 200
        assert response.headers["content-type"] == "application/json"

    def test_proxy_preserves_upstream_status_code(self, client: TestClient, mock_httpx_client: MagicMock) -> None:
        """Test that upstream status codes are preserved."""
        mock_httpx_client.request.return_value = make_response(201, b'{"created": true}')

        response = client.get("/")

        assert response.status_code == 201

    def test_proxy_preserves_404_status(self, client: TestClient, mock_httpx_client: MagicMock) -> None:
        """Test that 404 status from upstream is preserved."""
        mock_httpx_client.request.return_value = make_response(404, b'{"error": "not found"}')

        response = client.get("/nonexistent")

        assert response.status_code == 404
        assert response.headers["content-type"] == "application/json"

    def test_proxy_preserves_500_status(self, client: TestClient, mock_httpx_client: MagicMock) -> None:
        """Test that 500 status from upstream is preserved."""
        mock_httpx_client.request.return_value = make_response(500, b'{"error": "server error"}')

        response = client.get("/")

        assert response.status_code == 500

    def test_proxy_handles_empty_response(self, client: TestClient, mock_httpx_client: MagicMock) -> None:
        """Test that empty responses are handled."""
        mock_httpx_client.request.return_value = make_response(204, b"")

        response = client.get("/")

        assert response.status_code == 204
        assert response.content == b""

    def test_proxy_handles_large_response(self, client: TestClient, mock_httpx_client: MagicMock) -> None:
        """Test that large responses are handled."""
        large_content = b'{"data": "' + b"x" * 100000 + b'"}'
        mock_httpx_client.request.return_value = make_response(200, large_content)

        response = client.get("/")

        assert response.status_code == 200
        assert len(response.content) == len(large_content)

    def test_proxy_converts_text_html_to_json(self, client: TestClient, mock_httpx_client: MagicMock) -> None:
        """Test that text/html Content-Type is converted to application/json."""
        mock_httpx_client.request.return_value = make_response(200, b'{"key": "value"}', {"Content-Type": "text/html"})

        response = client.get("/")

        assert response.headers["content-type"] == "application/json"

    def test_proxy_converts_text_plain_to_json(self, client: TestClient, mock_httpx_client: MagicMock) -> None:
        """Test that text/plain Content-Type is converted to application/json."""
        mock_httpx_client.request.return_value = make_response(200, b'{"key": "value"}', {"Content-Type": "text/plain"})

        response = client.get("/")

        assert response.headers["content-type"] == "application/json"


class TestHTTPMethods:
    """Tests for HTTP method support."""

    def test_post_request(self, client: TestClient, mock_httpx_client: MagicMock) -> None:
        """Test POST requests are proxied."""
        mock_httpx_client.request.return_value = make_response(201, b'{"id": 1}')

        response = client.post("/users", json={"name": "test"})

        assert response.status_code == 201
        mock_httpx_client.request.assert_called_once()
        call_kwargs = mock_httpx_client.request.call_args[1]
        assert call_kwargs["method"] == "POST"

    def test_put_request(self, client: TestClient, mock_httpx_client: MagicMock) -> None:
        """Test PUT requests are proxied."""
        mock_httpx_client.request.return_value = make_response(200, b'{"updated": true}')

        response = client.put("/users/1", json={"name": "updated"})

        assert response.status_code == 200
        call_kwargs = mock_httpx_client.request.call_args[1]
        assert call_kwargs["method"] == "PUT"

    def test_delete_request(self, client: TestClient, mock_httpx_client: MagicMock) -> None:
        """Test DELETE requests are proxied."""
        mock_httpx_client.request.return_value = make_response(204, b"")

        response = client.delete("/users/1")

        assert response.status_code == 204
        call_kwargs = mock_httpx_client.request.call_args[1]
        assert call_kwargs["method"] == "DELETE"

    def test_patch_request(self, client: TestClient, mock_httpx_client: MagicMock) -> None:
        """Test PATCH requests are proxied."""
        mock_httpx_client.request.return_value = make_response(200, b'{"patched": true}')

        response = client.patch("/users/1", json={"name": "patched"})

        assert response.status_code == 200
        call_kwargs = mock_httpx_client.request.call_args[1]
        assert call_kwargs["method"] == "PATCH"

    def test_head_request(self, client: TestClient, mock_httpx_client: MagicMock) -> None:
        """Test HEAD requests are proxied."""
        mock_httpx_client.request.return_value = make_response(200, b"")

        response = client.head("/users")

        assert response.status_code == 200
        call_kwargs = mock_httpx_client.request.call_args[1]
        assert call_kwargs["method"] == "HEAD"


class TestQueryStringForwarding:
    """Tests for query string forwarding."""

    def test_query_string_forwarded(self, client: TestClient, mock_httpx_client: MagicMock) -> None:
        """Test that query strings are forwarded to upstream."""
        mock_httpx_client.request.return_value = make_response(200, b"[]")

        client.get("/users?page=1&limit=10")

        call_kwargs = mock_httpx_client.request.call_args[1]
        assert "page=1" in call_kwargs["url"]
        assert "limit=10" in call_kwargs["url"]

    def test_no_query_string(self, client: TestClient, mock_httpx_client: MagicMock) -> None:
        """Test requests without query strings work."""
        mock_httpx_client.request.return_value = make_response(200, b"{}")

        client.get("/users")

        call_kwargs = mock_httpx_client.request.call_args[1]
        assert "?" not in call_kwargs["url"]


class TestRequestBodyForwarding:
    """Tests for request body forwarding."""

    def test_json_body_forwarded(self, client: TestClient, mock_httpx_client: MagicMock) -> None:
        """Test that JSON body is forwarded to upstream."""
        mock_httpx_client.request.return_value = make_response(201, b'{"id": 1}')

        client.post("/users", json={"name": "test", "email": "test@example.com"})

        call_kwargs = mock_httpx_client.request.call_args[1]
        assert call_kwargs["content"] is not None
        assert b"test" in call_kwargs["content"]

    def test_empty_body_handled(self, client: TestClient, mock_httpx_client: MagicMock) -> None:
        """Test that empty body is handled."""
        mock_httpx_client.request.return_value = make_response(200, b"{}")

        client.get("/users")

        call_kwargs = mock_httpx_client.request.call_args[1]
        # Empty body should be None
        assert call_kwargs["content"] is None


class TestRequestHeaderForwarding:
    """Tests for request header forwarding."""

    def test_authorization_header_forwarded(self, client: TestClient, mock_httpx_client: MagicMock) -> None:
        """Test that Authorization header is forwarded."""
        mock_httpx_client.request.return_value = make_response(200, b"{}")

        client.get("/users", headers={"Authorization": "Bearer token123"})

        call_kwargs = mock_httpx_client.request.call_args[1]
        assert "authorization" in call_kwargs["headers"]
        assert call_kwargs["headers"]["authorization"] == "Bearer token123"

    def test_custom_x_headers_forwarded(self, client: TestClient, mock_httpx_client: MagicMock) -> None:
        """Test that X-* custom headers are forwarded."""
        mock_httpx_client.request.return_value = make_response(200, b"{}")

        client.get("/users", headers={"X-Custom-Header": "custom-value"})

        call_kwargs = mock_httpx_client.request.call_args[1]
        assert "x-custom-header" in call_kwargs["headers"]

    def test_host_header_not_forwarded(self, client: TestClient, mock_httpx_client: MagicMock) -> None:
        """Test that Host header is not forwarded."""
        mock_httpx_client.request.return_value = make_response(200, b"{}")

        client.get("/users")

        call_kwargs = mock_httpx_client.request.call_args[1]
        if call_kwargs["headers"]:
            assert "host" not in [h.lower() for h in call_kwargs["headers"].keys()]


class TestResponseHeaderPreservation:
    """Tests for response header preservation."""

    def test_upstream_headers_preserved(self, client: TestClient, mock_httpx_client: MagicMock) -> None:
        """Test that upstream headers are preserved."""
        mock_httpx_client.request.return_value = make_response(
            200, b"{}", {"X-Custom-Response": "value", "Cache-Control": "max-age=3600"}
        )

        response = client.get("/")

        assert response.headers.get("x-custom-response") == "value"
        assert response.headers.get("cache-control") == "max-age=3600"

    def test_content_type_overridden(self, client: TestClient, mock_httpx_client: MagicMock) -> None:
        """Test that Content-Type is always application/json."""
        mock_httpx_client.request.return_value = make_response(200, b"{}", {"Content-Type": "text/html"})

        response = client.get("/")

        assert response.headers["content-type"] == "application/json"


class TestPathForwarding:
    """Tests for path forwarding behavior."""

    def test_path_appended_to_target_url(self, mock_httpx_client: MagicMock) -> None:
        """Test that request path is appended to target URL."""
        mock_httpx_client.request.return_value = make_response(200, b"{}")

        with patch("json_force_proxy.server.get_settings") as mock_settings:
            mock_settings.return_value = Settings(target_url="https://api.example.com")

            with TestClient(app) as test_client:
                test_client.get("/users/123")

            call_kwargs = mock_httpx_client.request.call_args[1]
            assert call_kwargs["url"] == "https://api.example.com/users/123"

    def test_root_path_uses_base_url(self, mock_httpx_client: MagicMock) -> None:
        """Test that root path uses base URL."""
        mock_httpx_client.request.return_value = make_response(200, b"{}")

        with patch("json_force_proxy.server.get_settings") as mock_settings:
            mock_settings.return_value = Settings(target_url="https://api.example.com")

            with TestClient(app) as test_client:
                test_client.get("/")

            call_kwargs = mock_httpx_client.request.call_args[1]
            assert call_kwargs["url"] == "https://api.example.com"

    def test_trailing_slash_in_target_url_handled(self, mock_httpx_client: MagicMock) -> None:
        """Test that trailing slash in target URL is handled correctly."""
        mock_httpx_client.request.return_value = make_response(200, b"{}")

        with patch("json_force_proxy.server.get_settings") as mock_settings:
            mock_settings.return_value = Settings(target_url="https://api.example.com/")

            with TestClient(app) as test_client:
                test_client.get("/posts")

            call_kwargs = mock_httpx_client.request.call_args[1]
            assert call_kwargs["url"] == "https://api.example.com/posts"


class TestErrorHandling:
    """Tests for error handling."""

    def test_connection_refused_returns_502(self, client: TestClient, mock_httpx_client: MagicMock) -> None:
        """Test that connection refused errors return 502."""
        mock_httpx_client.request.side_effect = RequestError("Connection refused")

        response = client.get("/")

        assert response.status_code == 502
        assert b"Connection refused" in response.content

    def test_timeout_returns_502(self, client: TestClient, mock_httpx_client: MagicMock) -> None:
        """Test that timeout errors return 502."""
        mock_httpx_client.request.side_effect = TimeoutException("Request timed out")

        response = client.get("/")

        assert response.status_code == 502
        assert b"timed out" in response.content.lower()

    def test_dns_error_returns_502(self, client: TestClient, mock_httpx_client: MagicMock) -> None:
        """Test that DNS resolution errors return 502."""
        mock_httpx_client.request.side_effect = RequestError("Name resolution failed")

        response = client.get("/")

        assert response.status_code == 502

    def test_error_response_is_plain_text(self, client: TestClient, mock_httpx_client: MagicMock) -> None:
        """Test that error responses have text/plain Content-Type."""
        mock_httpx_client.request.side_effect = RequestError("Some error")

        response = client.get("/")

        assert "text/plain" in response.headers["content-type"]


class TestConfiguration:
    """Tests for configuration."""

    def test_settings_defaults(self) -> None:
        """Test that settings have sensible defaults."""
        import os

        # Temporarily remove target_url from env to test default
        os.environ.pop("JSON_FORCE_PROXY_TARGET_URL", None)
        get_settings.cache_clear()

        settings = Settings()
        assert settings.host == "0.0.0.0"
        assert settings.port == 8080
        assert settings.log_level == LogLevel.INFO
        assert settings.request_timeout == 10.0
        assert settings.target_url is None

    def test_settings_from_environment_target_url(self) -> None:
        """Test that target URL can be set from environment."""
        with patch.dict(
            "os.environ",
            {"JSON_FORCE_PROXY_TARGET_URL": "https://custom.example.com/api"},
        ):
            get_settings.cache_clear()
            settings = get_settings()
            assert settings.target_url == "https://custom.example.com/api"

    def test_settings_from_environment_port(self) -> None:
        """Test that port can be set from environment."""
        with patch.dict("os.environ", {"JSON_FORCE_PROXY_PORT": "9000"}):
            get_settings.cache_clear()
            settings = get_settings()
            assert settings.port == 9000

    def test_settings_cache(self) -> None:
        """Test that settings are cached."""
        settings1 = get_settings()
        settings2 = get_settings()
        assert settings1 is settings2


class TestCORS:
    """Tests for CORS configuration."""

    def test_cors_headers_present(self, client: TestClient, mock_httpx_client: MagicMock) -> None:
        """Test that CORS headers are present."""
        mock_httpx_client.request.return_value = make_response(200, b"{}")

        response = client.get("/", headers={"Origin": "http://localhost:3000"})

        assert "access-control-allow-origin" in response.headers

    def test_cors_allows_any_origin(self, client: TestClient, mock_httpx_client: MagicMock) -> None:
        """Test that CORS allows any origin."""
        mock_httpx_client.request.return_value = make_response(200, b"{}")

        response = client.get("/", headers={"Origin": "https://any-domain.example.com"})

        assert response.headers["access-control-allow-origin"] == "*"

    def test_cors_preflight_request(self, client: TestClient, mock_httpx_client: MagicMock) -> None:
        """Test that CORS preflight requests are handled."""
        mock_httpx_client.request.return_value = make_response(200, b"{}")

        response = client.options(
            "/",
            headers={
                "Origin": "http://localhost:3000",
                "Access-Control-Request-Method": "POST",
            },
        )

        assert response.status_code == 200
        assert "access-control-allow-origin" in response.headers


class TestLogging:
    """Tests for logging behavior."""

    def test_debug_logging_on_request(self, client: TestClient, mock_httpx_client: MagicMock) -> None:
        """Test that debug logging occurs on request."""
        mock_httpx_client.request.return_value = make_response(200, b"{}")

        with patch("json_force_proxy.server.logger") as mock_logger:
            client.get("/test/path")

            assert mock_logger.debug.called

    def test_error_logging_on_failure(self, client: TestClient, mock_httpx_client: MagicMock) -> None:
        """Test that error logging occurs on failure."""
        mock_httpx_client.request.side_effect = RequestError("Connection failed")

        with patch("json_force_proxy.server.logger") as mock_logger:
            client.get("/")

            mock_logger.error.assert_called()
