# json-force-proxy

A simple proxy server that fixes incorrect `Content-Type` headers for JSON responses.

Built with FastAPI and Typer.

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
uv sync
```

### Usage

```bash
# Run with defaults (port 8080, proxying the default target)
uv run json-force-proxy serve

# Custom port and target
uv run json-force-proxy serve --port 3000 --target http://example.com/api/data

# With auto-reload for development
uv run json-force-proxy serve --reload

# Show help
uv run json-force-proxy --help
```

The proxy will:
- Listen on the specified port (default: 8080)
- Fetch from the upstream URL
- Return the response with `Content-Type: application/json`

### Running Tests

```bash
uv run pytest
```
