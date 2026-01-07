"""CLI interface using Typer."""

import os
from typing import Annotated, Optional

import typer
import uvicorn

from json_force_proxy.settings import LogLevel, Settings, configure_logging, get_settings

app = typer.Typer(
    name="json-force-proxy",
    help="Proxy server that fixes incorrect Content-Type headers for JSON responses",
)


@app.command()
def serve(
    port: Annotated[Optional[int], typer.Option("--port", "-p", help="Port to listen on")] = None,
    host: Annotated[Optional[str], typer.Option("--host", "-H", help="Host to bind to")] = None,
    target: Annotated[Optional[str], typer.Option("--target", "-t", help="Target URL to proxy")] = None,
    reload: Annotated[Optional[bool], typer.Option("--reload", "-r", help="Enable auto-reload")] = None,
    log_level: Annotated[Optional[LogLevel], typer.Option("--log-level", "-l", help="Logging level")] = None,
) -> None:
    """Start the proxy server.

    Configuration is loaded from environment variables (JSON_FORCE_PROXY_* prefix)
    or a .env file. CLI options override environment settings.
    """
    # Load settings from environment/.env, then override with CLI options
    settings = get_settings()

    effective_host = host if host is not None else settings.host
    effective_port = port if port is not None else settings.port
    effective_target = target if target is not None else settings.target_url
    effective_reload = reload if reload is not None else settings.reload
    effective_log_level = log_level if log_level is not None else settings.log_level

    # Create effective settings for logging configuration
    effective_settings = Settings(
        host=effective_host,
        port=effective_port,
        target_url=effective_target,
        reload=effective_reload,
        log_level=effective_log_level,
        request_timeout=settings.request_timeout,
    )
    configure_logging(effective_settings)

    # Set environment variables so the server process picks them up
    os.environ["JSON_FORCE_PROXY_TARGET_URL"] = effective_target
    os.environ["JSON_FORCE_PROXY_REQUEST_TIMEOUT"] = str(effective_settings.request_timeout)
    get_settings.cache_clear()

    typer.echo(f"Proxying: {effective_target}")
    typer.echo(f"Listening on: http://{effective_host}:{effective_port}")
    typer.echo(f"Log level: {effective_log_level.value}")

    uvicorn.run(
        "json_force_proxy.server:app",
        host=effective_host,
        port=effective_port,
        reload=effective_reload,
        log_level=effective_log_level.value.lower(),
    )


if __name__ == "__main__":
    app()
