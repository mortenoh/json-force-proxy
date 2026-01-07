# json-force-proxy

A simple proxy server that fixes incorrect `Content-Type` headers for JSON responses.

Built with FastAPI, Typer, and Pydantic Settings. Requires Python 3.13+.

## The Problem

Some upstream services return JSON data but with an incorrect `Content-Type` header (e.g., `text/html` instead of `application/json`). This commonly happens when an nginx reverse proxy is misconfigured.

### Common Causes (nginx)

1. **Missing `proxy_pass_header`** - nginx isn't forwarding the upstream Content-Type:
   ```nginx
   location /api/ {
       proxy_pass http://upstream:port;
       # Content-Type from upstream is lost
   }
   ```

2. **`default_type text/html`** - nginx's default when it doesn't recognize/pass the type

3. **Explicit override** - an `add_header` directive is overwriting the type:
   ```nginx
   add_header Content-Type "text/html";  # overwrites everything
   ```

### nginx Fix

If you control the nginx server, fix it there:

```nginx
location /api/ {
    proxy_pass http://upstream:port;
    proxy_pass_header Content-Type;
}
```

Or explicitly set the correct type:

```nginx
location /api/endpoint {
    proxy_pass http://upstream:port;
    default_type application/json;
}
```

## Using This Proxy (Workaround)

If you don't control the nginx server, use this proxy as a workaround.

### Installation

```bash
make install
# or
uv sync
```

### Configuration

Configuration is loaded from environment variables (with `JSON_FORCE_PROXY_` prefix) or a `.env` file. CLI options override environment settings.

| Variable | CLI Option | Default | Description |
|----------|------------|---------|-------------|
| `JSON_FORCE_PROXY_HOST` | `--host`, `-H` | `0.0.0.0` | Host to bind to |
| `JSON_FORCE_PROXY_PORT` | `--port`, `-p` | `8080` | Port to listen on |
| `JSON_FORCE_PROXY_TARGET_URL` | `--target`, `-t` | - | Target URL to proxy |
| `JSON_FORCE_PROXY_RELOAD` | `--reload`, `-r` | `false` | Enable auto-reload |
| `JSON_FORCE_PROXY_LOG_LEVEL` | `--log-level`, `-l` | `INFO` | Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL) |
| `JSON_FORCE_PROXY_REQUEST_TIMEOUT` | - | `10.0` | HTTP request timeout in seconds |

Example `.env` file:

```env
JSON_FORCE_PROXY_HOST=127.0.0.1
JSON_FORCE_PROXY_PORT=9000
JSON_FORCE_PROXY_TARGET_URL=http://example.com/api/data
JSON_FORCE_PROXY_LOG_LEVEL=DEBUG
```

### Usage

```bash
# Run with defaults (using .env or environment variables)
uv run json-force-proxy serve

# Custom port and target (overrides env)
uv run json-force-proxy serve --port 3000 --target http://example.com/api/data

# With auto-reload and debug logging
uv run json-force-proxy serve --reload --log-level DEBUG

# Show help
uv run json-force-proxy --help
```

The proxy will:
- Listen on the specified port (default: 8080)
- Fetch from the upstream URL
- Return the response with `Content-Type: application/json`

### Make Targets

```bash
make install   # Install dependencies
make lint      # Run ruff format, ruff check, mypy, pyright
make test      # Run tests
make run       # Run the proxy server
make dist      # Build distribution packages (wheel + sdist)
make clean     # Clean up cache files
```

### Running Tests

```bash
make test
# or
uv run pytest
```
