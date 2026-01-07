# json-force-proxy

[![CI](https://github.com/mortenoh/json-force-proxy/actions/workflows/ci.yml/badge.svg)](https://github.com/mortenoh/json-force-proxy/actions/workflows/ci.yml)
[![Docker](https://github.com/mortenoh/json-force-proxy/actions/workflows/docker.yml/badge.svg)](https://github.com/mortenoh/json-force-proxy/actions/workflows/docker.yml)
[![Docs](https://github.com/mortenoh/json-force-proxy/actions/workflows/docs.yml/badge.svg)](https://mortenoh.github.io/json-force-proxy/)
[![GHCR](https://img.shields.io/badge/ghcr.io-mortenoh%2Fjson--force--proxy-blue)](https://github.com/mortenoh/json-force-proxy/pkgs/container/json-force-proxy)
[![Python 3.13+](https://img.shields.io/badge/python-3.13+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

A proxy server that forces `Content-Type: application/json` on all responses.

Use this when an upstream API returns JSON data but with the wrong Content-Type header (e.g., `text/html` instead of `application/json`).

## Installation

```bash
# Install as a global tool
uv tool install json-force-proxy --from git+https://github.com/mortenoh/json-force-proxy

# Or run directly without installing
uvx --from git+https://github.com/mortenoh/json-force-proxy json-force-proxy -t https://api.example.com

# Or use Docker
docker run -p 8080:8080 ghcr.io/mortenoh/json-force-proxy -t https://api.example.com
```

## Usage

```bash
json-force-proxy --target https://api.example.com
json-force-proxy -t https://api.example.com -p 3000 -l DEBUG

# Access via proxy
curl http://localhost:8080/users       # -> https://api.example.com/users
curl http://localhost:8080/posts/1     # -> https://api.example.com/posts/1
curl http://localhost:8080/data?page=1 # -> https://api.example.com/data?page=1
```

## Options

| Option | Description | Default |
|--------|-------------|---------|
| `-t, --target` | Target URL to proxy | (required) |
| `-p, --port` | Port to listen on | `8080` |
| `-H, --host` | Host to bind to | `0.0.0.0` |
| `-l, --log-level` | DEBUG, INFO, WARNING, ERROR, CRITICAL | `INFO` |

## Features

- **All HTTP methods**: GET, POST, PUT, DELETE, PATCH, HEAD, OPTIONS
- **Query string forwarding**: `?page=1&limit=10` passed to upstream
- **Request body forwarding**: JSON and other request bodies proxied
- **Request header forwarding**: Authorization, Accept, Content-Type, X-* headers
- **Response header preservation**: Upstream headers preserved (except Content-Type)
- **CORS enabled**: All origins allowed

## Configuration

Environment variables (prefix `JSON_FORCE_PROXY_`) or `.env` file. CLI options override environment settings.

| Environment Variable | Default |
|---------------------|---------|
| `JSON_FORCE_PROXY_TARGET_URL` | (required) |
| `JSON_FORCE_PROXY_PORT` | `8080` |
| `JSON_FORCE_PROXY_HOST` | `0.0.0.0` |
| `JSON_FORCE_PROXY_LOG_LEVEL` | `INFO` |
| `JSON_FORCE_PROXY_REQUEST_TIMEOUT` | `10.0` |

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
