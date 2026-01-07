"""FastAPI proxy server that fixes Content-Type for JSON responses."""

import logging

import httpx
from fastapi import FastAPI, Response
from fastapi.middleware.cors import CORSMiddleware

from json_force_proxy.settings import get_settings

logger = logging.getLogger(__name__)

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


@app.get("/")
async def proxy_root() -> Response:
    """Proxy the root path to the target URL."""
    return await proxy_request("")


@app.get("/{path:path}")
async def proxy_path(path: str) -> Response:
    """Proxy any path to the target URL."""
    return await proxy_request(path)


async def proxy_request(path: str) -> Response:
    """Fetch from upstream and return with correct Content-Type."""
    settings = get_settings()
    base_url = settings.target_url.rstrip("/")
    target_url = f"{base_url}/{path}" if path else base_url
    timeout = settings.request_timeout

    logger.debug("Proxying request to %s", target_url)

    try:
        async with httpx.AsyncClient(timeout=timeout) as client:
            response = await client.get(target_url)
            logger.debug("Received response with status %d", response.status_code)
            return Response(
                content=response.content,
                status_code=response.status_code,
                media_type="application/json",
            )
    except httpx.RequestError as e:
        logger.error("Error fetching upstream: %s", e)
        return Response(
            content=f"Error fetching upstream: {e}".encode(),
            status_code=502,
            media_type="text/plain",
        )
