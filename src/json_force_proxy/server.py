"""FastAPI proxy server that fixes Content-Type for JSON responses."""

import logging

import httpx
from fastapi import FastAPI, Request, Response
from fastapi.middleware.cors import CORSMiddleware

from json_force_proxy.settings import get_settings

logger = logging.getLogger(__name__)

# Headers to forward from client request to upstream
FORWARD_REQUEST_HEADERS = {
    "authorization",
    "accept",
    "content-type",
    "accept-encoding",
    "accept-language",
    "user-agent",
    "cache-control",
    "if-none-match",
    "if-modified-since",
}

# Headers to skip from upstream response (we handle these ourselves)
SKIP_RESPONSE_HEADERS = {
    "content-type",
    "content-encoding",
    "content-length",
    "transfer-encoding",
    "connection",
}

app = FastAPI(
    title="JSON Force Proxy",
    description="Proxy that fixes incorrect Content-Type headers for JSON responses",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.api_route("/", methods=["GET", "POST", "PUT", "DELETE", "PATCH", "HEAD", "OPTIONS"])
async def proxy_root(request: Request) -> Response:
    """Proxy the root path to the target URL."""
    return await proxy_request(request, "")


@app.api_route("/{path:path}", methods=["GET", "POST", "PUT", "DELETE", "PATCH", "HEAD", "OPTIONS"])
async def proxy_path(request: Request, path: str) -> Response:
    """Proxy any path to the target URL."""
    return await proxy_request(request, path)


def filter_request_headers(request: Request) -> dict[str, str]:
    """Filter request headers to forward to upstream."""
    headers: dict[str, str] = {}
    for name, value in request.headers.items():
        lower_name = name.lower()
        # Forward whitelisted headers and X-* custom headers
        if lower_name in FORWARD_REQUEST_HEADERS or lower_name.startswith("x-"):
            headers[name] = value
    return headers


def build_response_headers(upstream_headers: httpx.Headers) -> dict[str, str]:
    """Build response headers from upstream, excluding certain headers."""
    headers: dict[str, str] = {}
    for name, value in upstream_headers.items():
        if name.lower() not in SKIP_RESPONSE_HEADERS:
            headers[name] = value
    return headers


async def proxy_request(request: Request, path: str) -> Response:
    """Proxy request to upstream and return with correct Content-Type."""
    settings = get_settings()
    if not settings.target_url:
        return Response(
            content=b"Error: target_url not configured",
            status_code=500,
            media_type="text/plain",
        )
    base_url = settings.target_url.rstrip("/")
    target_url = f"{base_url}/{path}" if path else base_url

    # Append query string if present
    if request.url.query:
        target_url = f"{target_url}?{request.url.query}"

    timeout = settings.request_timeout
    method = request.method

    logger.debug("Proxying %s request to %s", method, target_url)

    try:
        # Get request body and headers
        body = await request.body()
        headers = filter_request_headers(request)

        async with httpx.AsyncClient(timeout=timeout) as client:
            response = await client.request(
                method=method,
                url=target_url,
                content=body if body else None,
                headers=headers if headers else None,
            )
            logger.debug("Received response with status %d", response.status_code)

            # Build response headers from upstream
            response_headers = build_response_headers(response.headers)

            return Response(
                content=response.content,
                status_code=response.status_code,
                headers=response_headers,
                media_type="application/json",
            )
    except httpx.RequestError as e:
        logger.error("Error fetching upstream: %s", e)
        return Response(
            content=f"Error fetching upstream: {e}".encode(),
            status_code=502,
            media_type="text/plain",
        )
