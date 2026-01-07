# json-force-proxy

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

## Quick Example

```bash
# Start the proxy
json-force-proxy --target https://api.example.com

# Access via proxy
curl http://localhost:8080/users       # -> https://api.example.com/users
curl http://localhost:8080/posts/1     # -> https://api.example.com/posts/1
curl http://localhost:8080/data?page=1 # -> https://api.example.com/data?page=1
```

## Features

- **All HTTP methods**: GET, POST, PUT, DELETE, PATCH, HEAD, OPTIONS
- **Query string forwarding**: `?page=1&limit=10` passed to upstream
- **Request body forwarding**: JSON and other request bodies proxied
- **Request header forwarding**: Authorization, Accept, Content-Type, X-* headers
- **Response header preservation**: Upstream headers preserved (except Content-Type)
- **CORS enabled**: All origins allowed
