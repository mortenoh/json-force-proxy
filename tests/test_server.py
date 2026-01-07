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
    """Reset settings cache before each test."""
    get_settings.cache_clear()
    yield
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


class TestProxyEndpoints:
    """Tests for proxy endpoints."""

    def test_successful_proxy_returns_json_content_type(self, client: TestClient, mock_httpx_client: MagicMock) -> None:
        """Test that successful responses have application/json Content-Type."""
        mock_httpx_client.get.return_value = HttpxResponse(200, content=b'{"key": "value"}')

        response = client.get("/")

        assert response.status_code == 200
        assert response.headers["content-type"] == "application/json"
        assert response.content == b'{"key": "value"}'

    def test_upstream_error_returns_502(self, client: TestClient, mock_httpx_client: MagicMock) -> None:
        """Test that upstream errors return 502 status."""
        mock_httpx_client.get.side_effect = RequestError("Connection refused")

        response = client.get("/")

        assert response.status_code == 502
        assert response.headers["content-type"] == "text/plain; charset=utf-8"
        assert b"Error fetching upstream" in response.content

    def test_proxy_root_path(self, client: TestClient, mock_httpx_client: MagicMock) -> None:
        """Test that root path proxies correctly."""
        mock_httpx_client.get.return_value = HttpxResponse(200, content=b'{"root": true}')

        response = client.get("/")

        assert response.status_code == 200
        assert response.json() == {"root": True}

    def test_proxy_nested_path(self, client: TestClient, mock_httpx_client: MagicMock) -> None:
        """Test that nested paths are proxied."""
        mock_httpx_client.get.return_value = HttpxResponse(200, content=b'{"path": "nested"}')

        response = client.get("/some/nested/path")

        assert response.status_code == 200
        assert response.headers["content-type"] == "application/json"

    def test_proxy_preserves_upstream_status_code(self, client: TestClient, mock_httpx_client: MagicMock) -> None:
        """Test that upstream status codes are preserved."""
        mock_httpx_client.get.return_value = HttpxResponse(201, content=b'{"created": true}')

        response = client.get("/")

        assert response.status_code == 201

    def test_proxy_preserves_404_status(self, client: TestClient, mock_httpx_client: MagicMock) -> None:
        """Test that 404 status from upstream is preserved."""
        mock_httpx_client.get.return_value = HttpxResponse(404, content=b'{"error": "not found"}')

        response = client.get("/nonexistent")

        assert response.status_code == 404
        assert response.headers["content-type"] == "application/json"

    def test_proxy_preserves_500_status(self, client: TestClient, mock_httpx_client: MagicMock) -> None:
        """Test that 500 status from upstream is preserved."""
        mock_httpx_client.get.return_value = HttpxResponse(500, content=b'{"error": "server error"}')

        response = client.get("/")

        assert response.status_code == 500

    def test_proxy_handles_empty_response(self, client: TestClient, mock_httpx_client: MagicMock) -> None:
        """Test that empty responses are handled."""
        mock_httpx_client.get.return_value = HttpxResponse(204, content=b"")

        response = client.get("/")

        assert response.status_code == 204
        assert response.content == b""

    def test_proxy_handles_large_response(self, client: TestClient, mock_httpx_client: MagicMock) -> None:
        """Test that large responses are handled."""
        large_content = b'{"data": "' + b"x" * 100000 + b'"}'
        mock_httpx_client.get.return_value = HttpxResponse(200, content=large_content)

        response = client.get("/")

        assert response.status_code == 200
        assert len(response.content) == len(large_content)

    def test_proxy_converts_text_html_to_json(self, client: TestClient, mock_httpx_client: MagicMock) -> None:
        """Test that text/html Content-Type is converted to application/json."""
        mock_httpx_client.get.return_value = HttpxResponse(
            200, content=b'{"key": "value"}', headers={"Content-Type": "text/html"}
        )

        response = client.get("/")

        assert response.headers["content-type"] == "application/json"

    def test_proxy_converts_text_plain_to_json(self, client: TestClient, mock_httpx_client: MagicMock) -> None:
        """Test that text/plain Content-Type is converted to application/json."""
        mock_httpx_client.get.return_value = HttpxResponse(
            200, content=b'{"key": "value"}', headers={"Content-Type": "text/plain"}
        )

        response = client.get("/")

        assert response.headers["content-type"] == "application/json"


class TestPathForwarding:
    """Tests for path forwarding behavior."""

    def test_path_appended_to_target_url(self, mock_httpx_client: MagicMock) -> None:
        """Test that request path is appended to target URL."""
        mock_httpx_client.get.return_value = HttpxResponse(200, content=b"{}")

        with patch("json_force_proxy.server.get_settings") as mock_settings:
            mock_settings.return_value = Settings(target_url="https://api.example.com")

            with TestClient(app) as client:
                client.get("/users/123")

            mock_httpx_client.get.assert_called_with("https://api.example.com/users/123")

    def test_root_path_uses_base_url(self, mock_httpx_client: MagicMock) -> None:
        """Test that root path uses base URL without trailing slash duplication."""
        mock_httpx_client.get.return_value = HttpxResponse(200, content=b"{}")

        with patch("json_force_proxy.server.get_settings") as mock_settings:
            mock_settings.return_value = Settings(target_url="https://api.example.com")

            with TestClient(app) as client:
                client.get("/")

            mock_httpx_client.get.assert_called_with("https://api.example.com")

    def test_trailing_slash_in_target_url_handled(self, mock_httpx_client: MagicMock) -> None:
        """Test that trailing slash in target URL is handled correctly."""
        mock_httpx_client.get.return_value = HttpxResponse(200, content=b"{}")

        with patch("json_force_proxy.server.get_settings") as mock_settings:
            mock_settings.return_value = Settings(target_url="https://api.example.com/")

            with TestClient(app) as client:
                client.get("/posts")

            mock_httpx_client.get.assert_called_with("https://api.example.com/posts")

    def test_deeply_nested_path(self, mock_httpx_client: MagicMock) -> None:
        """Test deeply nested paths are forwarded correctly."""
        mock_httpx_client.get.return_value = HttpxResponse(200, content=b"{}")

        with patch("json_force_proxy.server.get_settings") as mock_settings:
            mock_settings.return_value = Settings(target_url="https://api.example.com")

            with TestClient(app) as client:
                client.get("/api/v1/users/123/posts/456/comments")

            mock_httpx_client.get.assert_called_with("https://api.example.com/api/v1/users/123/posts/456/comments")


class TestErrorHandling:
    """Tests for error handling."""

    def test_connection_refused_returns_502(self, client: TestClient, mock_httpx_client: MagicMock) -> None:
        """Test that connection refused errors return 502."""
        mock_httpx_client.get.side_effect = RequestError("Connection refused")

        response = client.get("/")

        assert response.status_code == 502
        assert b"Connection refused" in response.content

    def test_timeout_returns_502(self, client: TestClient, mock_httpx_client: MagicMock) -> None:
        """Test that timeout errors return 502."""
        mock_httpx_client.get.side_effect = TimeoutException("Request timed out")

        response = client.get("/")

        assert response.status_code == 502
        assert b"timed out" in response.content.lower()

    def test_dns_error_returns_502(self, client: TestClient, mock_httpx_client: MagicMock) -> None:
        """Test that DNS resolution errors return 502."""
        mock_httpx_client.get.side_effect = RequestError("Name resolution failed")

        response = client.get("/")

        assert response.status_code == 502

    def test_error_response_is_plain_text(self, client: TestClient, mock_httpx_client: MagicMock) -> None:
        """Test that error responses have text/plain Content-Type."""
        mock_httpx_client.get.side_effect = RequestError("Some error")

        response = client.get("/")

        assert "text/plain" in response.headers["content-type"]


class TestConfiguration:
    """Tests for configuration."""

    def test_settings_defaults(self) -> None:
        """Test that settings have sensible defaults."""
        settings = Settings()
        assert settings.host == "0.0.0.0"
        assert settings.port == 8080
        assert settings.reload is False
        assert settings.log_level == LogLevel.INFO
        assert settings.request_timeout == 10.0
        assert settings.target_url == "https://jsonplaceholder.typicode.com"

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

    def test_settings_from_environment_host(self) -> None:
        """Test that host can be set from environment."""
        with patch.dict("os.environ", {"JSON_FORCE_PROXY_HOST": "127.0.0.1"}):
            get_settings.cache_clear()
            settings = get_settings()
            assert settings.host == "127.0.0.1"

    def test_settings_from_environment_reload(self) -> None:
        """Test that reload can be set from environment."""
        with patch.dict("os.environ", {"JSON_FORCE_PROXY_RELOAD": "true"}):
            get_settings.cache_clear()
            settings = get_settings()
            assert settings.reload is True

    def test_settings_from_environment_log_level(self) -> None:
        """Test that log level can be set from environment."""
        with patch.dict("os.environ", {"JSON_FORCE_PROXY_LOG_LEVEL": "DEBUG"}):
            get_settings.cache_clear()
            settings = get_settings()
            assert settings.log_level == LogLevel.DEBUG

    def test_settings_from_environment_timeout(self) -> None:
        """Test that timeout can be set from environment."""
        with patch.dict("os.environ", {"JSON_FORCE_PROXY_REQUEST_TIMEOUT": "30.0"}):
            get_settings.cache_clear()
            settings = get_settings()
            assert settings.request_timeout == 30.0

    def test_settings_cache(self) -> None:
        """Test that settings are cached."""
        settings1 = get_settings()
        settings2 = get_settings()
        assert settings1 is settings2

    def test_settings_cache_clear(self) -> None:
        """Test that settings cache can be cleared."""
        settings1 = get_settings()
        get_settings.cache_clear()
        settings2 = get_settings()
        assert settings1 is not settings2

    def test_all_log_levels_valid(self) -> None:
        """Test that all log levels are valid."""
        for level in LogLevel:
            settings = Settings(log_level=level)
            assert settings.log_level == level


class TestCORS:
    """Tests for CORS configuration."""

    def test_cors_headers_present(self, client: TestClient, mock_httpx_client: MagicMock) -> None:
        """Test that CORS headers are present."""
        mock_httpx_client.get.return_value = HttpxResponse(200, content=b"{}")

        response = client.get("/", headers={"Origin": "http://localhost:3000"})

        assert "access-control-allow-origin" in response.headers

    def test_cors_allows_any_origin(self, client: TestClient, mock_httpx_client: MagicMock) -> None:
        """Test that CORS allows any origin."""
        mock_httpx_client.get.return_value = HttpxResponse(200, content=b"{}")

        response = client.get("/", headers={"Origin": "https://any-domain.example.com"})

        assert response.headers["access-control-allow-origin"] == "*"

    def test_cors_preflight_request(self, client: TestClient) -> None:
        """Test that CORS preflight requests are handled."""
        response = client.options(
            "/",
            headers={
                "Origin": "http://localhost:3000",
                "Access-Control-Request-Method": "GET",
            },
        )

        assert response.status_code == 200
        assert "access-control-allow-origin" in response.headers


class TestRequestTimeout:
    """Tests for request timeout configuration."""

    def test_timeout_passed_to_client(self, mock_httpx_client: MagicMock) -> None:
        """Test that timeout is passed to httpx client."""
        mock_httpx_client.get.return_value = HttpxResponse(200, content=b"{}")

        with patch("json_force_proxy.server.get_settings") as mock_settings:
            mock_settings.return_value = Settings(request_timeout=5.0)

            with TestClient(app) as client:
                client.get("/")

        # The AsyncClient is called with timeout parameter
        with patch("json_force_proxy.server.httpx.AsyncClient") as mock_async_client:
            mock_instance = AsyncMock()
            mock_instance.get.return_value = HttpxResponse(200, content=b"{}")
            mock_instance.__aenter__.return_value = mock_instance
            mock_instance.__aexit__.return_value = None
            mock_async_client.return_value = mock_instance

            with patch("json_force_proxy.server.get_settings") as mock_settings:
                mock_settings.return_value = Settings(request_timeout=15.0)

                with TestClient(app) as client:
                    client.get("/")

                mock_async_client.assert_called_with(timeout=15.0)


class TestLogging:
    """Tests for logging behavior."""

    def test_debug_logging_on_request(self, client: TestClient, mock_httpx_client: MagicMock) -> None:
        """Test that debug logging occurs on request."""
        mock_httpx_client.get.return_value = HttpxResponse(200, content=b"{}")

        with patch("json_force_proxy.server.logger") as mock_logger:
            client.get("/test/path")

            # Verify debug was called (at least for the request)
            assert mock_logger.debug.called

    def test_error_logging_on_failure(self, client: TestClient, mock_httpx_client: MagicMock) -> None:
        """Test that error logging occurs on failure."""
        mock_httpx_client.get.side_effect = RequestError("Connection failed")

        with patch("json_force_proxy.server.logger") as mock_logger:
            client.get("/")

            mock_logger.error.assert_called()
