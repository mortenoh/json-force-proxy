# Usage

## Command Line Options

| Option | Description | Default |
|--------|-------------|---------|
| `-t, --target` | Target URL to proxy | (required) |
| `-p, --port` | Port to listen on | `8080` |
| `-H, --host` | Host to bind to | `0.0.0.0` |
| `-l, --log-level` | DEBUG, INFO, WARNING, ERROR, CRITICAL | `INFO` |

## Examples

```bash
# Basic usage
json-force-proxy --target https://api.example.com

# Custom port
json-force-proxy --target https://api.example.com --port 3000

# Debug logging
json-force-proxy --target https://api.example.com --log-level DEBUG

# Short options
json-force-proxy -t https://api.example.com -p 3000 -l DEBUG
```

## HTTP Methods

All HTTP methods are supported and forwarded to the upstream:

```bash
# GET
curl http://localhost:8080/users

# POST
curl -X POST http://localhost:8080/users -H "Content-Type: application/json" -d '{"name": "John"}'

# PUT
curl -X PUT http://localhost:8080/users/1 -H "Content-Type: application/json" -d '{"name": "Jane"}'

# DELETE
curl -X DELETE http://localhost:8080/users/1
```

## Headers

### Forwarded Request Headers

The following headers are forwarded to the upstream:

- `Authorization`
- `Accept`
- `Content-Type`
- `Accept-Encoding`
- `Accept-Language`
- `User-Agent`
- `Cache-Control`
- `If-None-Match`
- `If-Modified-Since`
- All `X-*` custom headers

### Response Headers

All response headers from the upstream are preserved, except:

- `Content-Type` (forced to `application/json`)
- `Content-Encoding`
- `Content-Length`
- `Transfer-Encoding`
- `Connection`

## Docker

```bash
# Run with Docker
docker run -p 8080:8080 ghcr.io/mortenoh/json-force-proxy -t https://api.example.com

# With environment variables
docker run -p 8080:8080 \
  -e JSON_FORCE_PROXY_TARGET_URL=https://api.example.com \
  -e JSON_FORCE_PROXY_LOG_LEVEL=DEBUG \
  ghcr.io/mortenoh/json-force-proxy

# Custom port mapping
docker run -p 3000:8080 ghcr.io/mortenoh/json-force-proxy -t https://api.example.com
```
