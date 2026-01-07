"""Tests for the proxy server."""

from collections.abc import Generator
from unittest.mock import AsyncMock, patch

import pytest
from fastapi.testclient import TestClient
from httpx import RequestError
from httpx import Response as HttpxResponse

from json_force_proxy.server import app
from json_force_proxy.settings import Settings, get_settings


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


class TestProxyEndpoints:
    """Tests for proxy endpoints."""

    def test_successful_proxy_returns_json_content_type(self, client: TestClient) -> None:
        """Test that successful responses have application/json Content-Type."""
        mock_response = HttpxResponse(200, content=b'{"key": "value"}')

        with patch("json_force_proxy.server.httpx.AsyncClient") as mock_client:
            mock_instance = AsyncMock()
            mock_instance.get.return_value = mock_response
            mock_instance.__aenter__.return_value = mock_instance
            mock_instance.__aexit__.return_value = None
            mock_client.return_value = mock_instance

            response = client.get("/")

            assert response.status_code == 200
            assert response.headers["content-type"] == "application/json"
            assert response.content == b'{"key": "value"}'

    def test_upstream_error_returns_502(self, client: TestClient) -> None:
        """Test that upstream errors return 502 status."""
        with patch("json_force_proxy.server.httpx.AsyncClient") as mock_client:
            mock_instance = AsyncMock()
            mock_instance.get.side_effect = RequestError("Connection refused")
            mock_instance.__aenter__.return_value = mock_instance
            mock_instance.__aexit__.return_value = None
            mock_client.return_value = mock_instance

            response = client.get("/")

            assert response.status_code == 502
            assert response.headers["content-type"] == "text/plain; charset=utf-8"
            assert b"Error fetching upstream" in response.content

    def test_proxy_any_path(self, client: TestClient) -> None:
        """Test that any path is proxied."""
        mock_response = HttpxResponse(200, content=b'{"path": "test"}')

        with patch("json_force_proxy.server.httpx.AsyncClient") as mock_client:
            mock_instance = AsyncMock()
            mock_instance.get.return_value = mock_response
            mock_instance.__aenter__.return_value = mock_instance
            mock_instance.__aexit__.return_value = None
            mock_client.return_value = mock_instance

            response = client.get("/some/nested/path")

            assert response.status_code == 200
            assert response.headers["content-type"] == "application/json"


class TestConfiguration:
    """Tests for configuration functions."""

    def test_settings_from_environment(self) -> None:
        """Test that settings can be loaded from environment."""
        with patch.dict(
            "os.environ",
            {"JSON_FORCE_PROXY_TARGET_URL": "http://custom.example.com/endpoint"},
        ):
            get_settings.cache_clear()
            settings = get_settings()
            assert settings.target_url == "http://custom.example.com/endpoint"

    def test_settings_defaults(self) -> None:
        """Test that settings have sensible defaults."""
        settings = Settings()
        assert settings.host == "0.0.0.0"
        assert settings.port == 8080
        assert settings.reload is False

    def test_cors_headers(self, client: TestClient) -> None:
        """Test that CORS headers are present."""
        mock_response = HttpxResponse(200, content=b"{}")

        with patch("json_force_proxy.server.httpx.AsyncClient") as mock_client:
            mock_instance = AsyncMock()
            mock_instance.get.return_value = mock_response
            mock_instance.__aenter__.return_value = mock_instance
            mock_instance.__aexit__.return_value = None
            mock_client.return_value = mock_instance

            response = client.get("/", headers={"Origin": "http://localhost:3000"})

            assert "access-control-allow-origin" in response.headers
