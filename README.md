# json-force-proxy

A proxy server that forces `Content-Type: application/json` on all responses.

Use this when an upstream API returns JSON data but with the wrong Content-Type header (e.g., `text/html` instead of `application/json`).

## Installation

```bash
# Install as a global tool
uv tool install json-force-proxy --from git+https://github.com/mortenoh/json-force-proxy

# Now run it
json-force-proxy --target https://api.example.com
```

## Quick Start

```bash
# Start proxy (after installation)
json-force-proxy --target https://jsonplaceholder.typicode.com

# Or run directly without installing
uvx --from git+https://github.com/mortenoh/json-force-proxy json-force-proxy -t https://jsonplaceholder.typicode.com

# Access via proxy - paths are forwarded to target
curl http://localhost:8080/users      # -> https://jsonplaceholder.typicode.com/users
curl http://localhost:8080/posts/1    # -> https://jsonplaceholder.typicode.com/posts/1
```

## Example

Upstream API returns JSON with wrong Content-Type:

```bash
$ curl -I https://broken-api.example.com/data
Content-Type: text/html; charset=utf-8   # Wrong!

$ curl https://broken-api.example.com/data
{"status": "ok", "data": [...]}          # But it's JSON
```

Use json-force-proxy to fix it:

```bash
$ json-force-proxy --target https://broken-api.example.com

$ curl -I http://localhost:8080/data
Content-Type: application/json           # Fixed!
```

## Features

- **All HTTP methods**: GET, POST, PUT, DELETE, PATCH, HEAD, OPTIONS
- **Query string forwarding**: `?page=1&limit=10` passed to upstream
- **Request body forwarding**: JSON and other request bodies proxied
- **Request header forwarding**: Authorization, Accept, Content-Type, and X-* headers
- **Response header preservation**: Upstream headers preserved (except Content-Type)
- **CORS enabled**: All origins allowed

## CLI Usage

```
Usage: json-force-proxy [OPTIONS]

Options:
  -t, --target TEXT      Target URL to proxy (required)
  -p, --port INTEGER     Port to listen on (default: 8080)
  -H, --host TEXT        Host to bind to (default: 0.0.0.0)
  -l, --log-level LEVEL  DEBUG, INFO, WARNING, ERROR, CRITICAL (default: INFO)
  --help                 Show this message and exit
```

Examples:

```bash
# Proxy to a specific API
json-force-proxy --target https://api.example.com

# Custom port
json-force-proxy --target https://api.example.com --port 3000

# Debug logging
json-force-proxy --target https://api.example.com --log-level DEBUG

# Short options
json-force-proxy -t https://api.example.com -p 3000 -l DEBUG
```

## Configuration

Settings can be configured via environment variables or a `.env` file. CLI options override environment settings.

| Environment Variable | CLI Option | Default |
|---------------------|------------|---------|
| `JSON_FORCE_PROXY_TARGET_URL` | `--target`, `-t` | (required) |
| `JSON_FORCE_PROXY_PORT` | `--port`, `-p` | `8080` |
| `JSON_FORCE_PROXY_HOST` | `--host`, `-H` | `0.0.0.0` |
| `JSON_FORCE_PROXY_LOG_LEVEL` | `--log-level`, `-l` | `INFO` |
| `JSON_FORCE_PROXY_REQUEST_TIMEOUT` | - | `10.0` |

Example `.env` file:

```env
JSON_FORCE_PROXY_TARGET_URL=https://api.example.com
JSON_FORCE_PROXY_PORT=9000
JSON_FORCE_PROXY_LOG_LEVEL=DEBUG
```

## Development

Requires Python 3.13+.

```bash
make install   # Install dependencies
make lint      # Run ruff, mypy, pyright
make test      # Run tests
make run       # Run the proxy server
make dist      # Build wheel + sdist
make clean     # Clean up cache files
```
