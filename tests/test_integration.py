"""Integration tests with a mock upstream server."""

import json
import threading
import time
from collections.abc import Generator

import pytest
import uvicorn
from fastapi import FastAPI, Request, Response
from fastapi.testclient import TestClient

from json_force_proxy.server import app as proxy_app
from json_force_proxy.settings import get_settings


def create_mock_upstream() -> FastAPI:
    """Create a mock upstream server that returns JSON with wrong content-types."""
    app = FastAPI()

    def make_json_response(content_type: str) -> Response:
        return Response(content=f'{{"type": "{content_type}"}}'.encode(), media_type=content_type)

    # Common wrong content-types
    app.add_api_route("/text-html", lambda: make_json_response("text/html"))
    app.add_api_route("/text-plain", lambda: make_json_response("text/plain"))
    app.add_api_route("/text-xml", lambda: make_json_response("text/xml"))
    app.add_api_route("/application-xml", lambda: make_json_response("application/xml"))
    app.add_api_route("/application-octet-stream", lambda: make_json_response("application/octet-stream"))

    # Weird/invalid content-types
    app.add_api_route("/weird-a-x", lambda: make_json_response("a/x"))
    app.add_api_route("/weird-foo-bar", lambda: make_json_response("foo/bar"))
    app.add_api_route("/weird-x-custom", lambda: make_json_response("x-custom/json-like"))

    def empty_content_type() -> Response:
        return Response(content=b'{"type": "none"}', headers={"content-type": ""})

    def no_content_type() -> Response:
        resp = Response(content=b'{"type": "missing"}')
        del resp.headers["content-type"]
        return resp

    app.add_api_route("/empty-content-type", empty_content_type)
    app.add_api_route("/no-content-type", no_content_type)

    # Correct content-type (should still work)
    app.add_api_route("/correct-json", lambda: make_json_response("application/json"))
    app.add_api_route(
        "/json-charset",
        lambda: Response(content=b'{"type": "json+charset"}', media_type="application/json; charset=utf-8"),
    )

    def with_query(foo: str = "", bar: str = "") -> Response:
        return Response(content=f'{{"foo": "{foo}", "bar": "{bar}"}}'.encode(), media_type="text/html")

    async def echo_body(request: Request) -> Response:
        body = await request.body()
        return Response(content=body, media_type="text/plain")

    def echo_headers(request: Request) -> Response:
        headers = {
            "authorization": request.headers.get("authorization", ""),
            "x-custom": request.headers.get("x-custom", ""),
        }
        return Response(content=json.dumps(headers).encode(), media_type="text/html")

    def custom_headers() -> Response:
        return Response(
            content=b'{"has_headers": true}',
            media_type="text/html",
            headers={"X-Custom-Response": "test-value", "Cache-Control": "no-cache"},
        )

    def method_test(request: Request) -> Response:
        return Response(content=f'{{"method": "{request.method}"}}'.encode(), media_type="text/html")

    app.add_api_route("/with-query", with_query)
    app.add_api_route("/echo-body", echo_body, methods=["POST"])
    app.add_api_route("/echo-headers", echo_headers)
    app.add_api_route("/custom-headers", custom_headers)
    app.add_api_route("/method-test", method_test, methods=["GET", "POST", "PUT", "DELETE", "PATCH"])

    return app


class MockServer:
    """A mock server that runs in a background thread."""

    def __init__(self, app: FastAPI, port: int) -> None:
        self.app = app
        self.port = port
        self.server: uvicorn.Server | None = None
        self.thread: threading.Thread | None = None

    def start(self) -> None:
        """Start the server in a background thread."""
        config = uvicorn.Config(
            self.app,
            host="127.0.0.1",
            port=self.port,
            log_level="error",
        )
        self.server = uvicorn.Server(config)
        self.thread = threading.Thread(target=self.server.run, daemon=True)
        self.thread.start()
        # Wait for server to start
        time.sleep(0.5)

    def stop(self) -> None:
        """Stop the server."""
        if self.server:
            self.server.should_exit = True
        if self.thread:
            self.thread.join(timeout=1)


@pytest.fixture
def mock_upstream() -> Generator[str, None, None]:
    """Start a mock upstream server and return its URL."""
    port = 19876
    app = create_mock_upstream()
    server = MockServer(app, port)
    server.start()
    yield f"http://127.0.0.1:{port}"
    server.stop()


@pytest.fixture
def proxy_client(mock_upstream: str) -> Generator[TestClient, None, None]:
    """Create a test client for the proxy, configured to use mock upstream."""
    import os

    os.environ["JSON_FORCE_PROXY_TARGET_URL"] = mock_upstream
    get_settings.cache_clear()
    yield TestClient(proxy_app)
    os.environ.pop("JSON_FORCE_PROXY_TARGET_URL", None)
    get_settings.cache_clear()


class TestContentTypeFixing:
    """Test that the proxy fixes Content-Type headers."""

    @pytest.mark.parametrize(
        "path,expected_type",
        [
            # Common wrong content-types
            ("/text-html", "text/html"),
            ("/text-plain", "text/plain"),
            ("/text-xml", "text/xml"),
            ("/application-xml", "application/xml"),
            ("/application-octet-stream", "application/octet-stream"),
            # Weird/invalid content-types
            ("/weird-a-x", "a/x"),
            ("/weird-foo-bar", "foo/bar"),
            ("/weird-x-custom", "x-custom/json-like"),
        ],
    )
    def test_fixes_wrong_content_type(self, proxy_client: TestClient, path: str, expected_type: str) -> None:
        """Test that wrong content-types are converted to application/json."""
        response = proxy_client.get(path)

        assert response.status_code == 200
        assert response.headers["content-type"] == "application/json"
        assert response.json()["type"] == expected_type

    def test_fixes_empty_content_type(self, proxy_client: TestClient) -> None:
        """Test that empty content-type is converted to application/json."""
        response = proxy_client.get("/empty-content-type")

        assert response.status_code == 200
        assert response.headers["content-type"] == "application/json"

    def test_fixes_missing_content_type(self, proxy_client: TestClient) -> None:
        """Test that missing content-type is converted to application/json."""
        response = proxy_client.get("/no-content-type")

        assert response.status_code == 200
        assert response.headers["content-type"] == "application/json"

    def test_correct_json_still_works(self, proxy_client: TestClient) -> None:
        """Test that already correct content-type still works."""
        response = proxy_client.get("/correct-json")

        assert response.status_code == 200
        assert response.headers["content-type"] == "application/json"
        assert response.json() == {"type": "application/json"}

    def test_json_with_charset_still_works(self, proxy_client: TestClient) -> None:
        """Test that json with charset works."""
        response = proxy_client.get("/json-charset")

        assert response.status_code == 200
        assert response.headers["content-type"] == "application/json"


class TestQueryStringForwarding:
    """Test that query strings are forwarded."""

    def test_query_params_forwarded(self, proxy_client: TestClient) -> None:
        """Test that query parameters are passed to upstream."""
        response = proxy_client.get("/with-query?foo=hello&bar=world")

        assert response.status_code == 200
        data = response.json()
        assert data["foo"] == "hello"
        assert data["bar"] == "world"


class TestRequestBodyForwarding:
    """Test that request bodies are forwarded."""

    def test_post_body_forwarded(self, proxy_client: TestClient) -> None:
        """Test that POST body is passed to upstream."""
        response = proxy_client.post("/echo-body", json={"test": "data"})

        assert response.status_code == 200
        assert response.json() == {"test": "data"}


class TestHeaderForwarding:
    """Test that headers are forwarded correctly."""

    def test_authorization_header_forwarded(self, proxy_client: TestClient) -> None:
        """Test that Authorization header is passed to upstream."""
        response = proxy_client.get(
            "/echo-headers",
            headers={"Authorization": "Bearer test-token"},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["authorization"] == "Bearer test-token"

    def test_custom_x_header_forwarded(self, proxy_client: TestClient) -> None:
        """Test that X-* headers are passed to upstream."""
        response = proxy_client.get(
            "/echo-headers",
            headers={"X-Custom": "custom-value"},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["x-custom"] == "custom-value"


class TestResponseHeaderPreservation:
    """Test that response headers are preserved."""

    def test_custom_response_headers_preserved(self, proxy_client: TestClient) -> None:
        """Test that custom headers from upstream are preserved."""
        response = proxy_client.get("/custom-headers")

        assert response.status_code == 200
        assert response.headers.get("x-custom-response") == "test-value"
        assert response.headers.get("cache-control") == "no-cache"
        # But content-type should be fixed
        assert response.headers["content-type"] == "application/json"


class TestHTTPMethods:
    """Test that all HTTP methods work."""

    def test_get_method(self, proxy_client: TestClient) -> None:
        """Test GET requests."""
        response = proxy_client.get("/method-test")
        assert response.json() == {"method": "GET"}

    def test_post_method(self, proxy_client: TestClient) -> None:
        """Test POST requests."""
        response = proxy_client.post("/method-test")
        assert response.json() == {"method": "POST"}

    def test_put_method(self, proxy_client: TestClient) -> None:
        """Test PUT requests."""
        response = proxy_client.put("/method-test")
        assert response.json() == {"method": "PUT"}

    def test_delete_method(self, proxy_client: TestClient) -> None:
        """Test DELETE requests."""
        response = proxy_client.delete("/method-test")
        assert response.json() == {"method": "DELETE"}

    def test_patch_method(self, proxy_client: TestClient) -> None:
        """Test PATCH requests."""
        response = proxy_client.patch("/method-test")
        assert response.json() == {"method": "PATCH"}
