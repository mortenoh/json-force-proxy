# Configuration

Settings can be configured via environment variables or a `.env` file. CLI options override environment settings.

## Environment Variables

| Environment Variable | Default |
|---------------------|---------|
| `JSON_FORCE_PROXY_TARGET_URL` | (required) |
| `JSON_FORCE_PROXY_PORT` | `8080` |
| `JSON_FORCE_PROXY_HOST` | `0.0.0.0` |
| `JSON_FORCE_PROXY_LOG_LEVEL` | `INFO` |
| `JSON_FORCE_PROXY_REQUEST_TIMEOUT` | `10.0` |

## Example .env File

```env
JSON_FORCE_PROXY_TARGET_URL=https://api.example.com
JSON_FORCE_PROXY_PORT=9000
JSON_FORCE_PROXY_LOG_LEVEL=DEBUG
JSON_FORCE_PROXY_REQUEST_TIMEOUT=30.0
```

## Priority

Configuration is loaded in the following order (later overrides earlier):

1. Default values
2. `.env` file
3. Environment variables
4. CLI options
