# Deployment Guide

This guide covers running petfishFramework in production using Docker and
Docker Compose.

## Quick Start

Build and run the container:

```bash
docker build -t petfishframework .
docker run --rm -e OPENAI_API_KEY=$OPENAI_API_KEY petfishframework
```

With Docker Compose:

```bash
docker compose up --build
```

## Dockerfile

The included `Dockerfile` uses a multi-stage style with `uv`:

1. Copies `pyproject.toml` and `uv.lock` first for layer caching.
2. Installs production dependencies with `uv sync --no-dev`.
3. Copies the `src/` directory and installs the package itself.
4. Uses `ENTRYPOINT ["python", "-m", "petfishframework"]`.

To build for a specific Python version, change the base image tag:

```dockerfile
FROM python:3.11-slim
```

## Environment Variables

The container reads configuration from environment variables. Required and
commonly used variables:

| Variable | Purpose | Example |
|---|---|---|
| `OPENAI_API_KEY` | API key for OpenAI-compatible models | `sk-...` |
| `OPENAI_BASE_URL` | Custom base URL for OpenAI-compatible endpoints | `https://api.siliconflow.cn/v1` |
| `ANTHROPIC_API_KEY` | API key for Anthropic models | `sk-ant-...` |
| `VAULT_ADDR` | HashiCorp Vault URL when using `VaultCredentialSource` | `https://vault.example.com` |
| `VAULT_TOKEN` | Vault token (alternative to passing it in code) | `hvs.CAES...` |

Pass variables with `-e`:

```bash
docker run --rm \
  -e OPENAI_API_KEY=$OPENAI_API_KEY \
  -e OPENAI_BASE_URL=$OPENAI_BASE_URL \
  petfishframework
```

Or use an `.env` file:

```bash
docker run --rm --env-file .env petfishframework
```

## Volume Mounts

Mount directories that the framework needs at runtime:

### Examples and local policies

```bash
docker run --rm \
  -e OPENAI_API_KEY=$OPENAI_API_KEY \
  -v $(pwd)/examples:/app/examples \
  -v $(pwd)/policies:/app/policies \
  petfishframework python examples/05_enterprise_expense.py
```

### Credentials and secrets

Do **not** bake credentials into the image. Instead, use one of these
approaches:

1. **Environment variables** — simplest for container runtimes.
2. **Secret mounts** — Docker secrets or Kubernetes secrets mounted as files.
3. **Vault integration** — use `VaultCredentialSource` to fetch secrets at
   startup; see the [Credential Broker](#credential-broker) section below.

For policy files, YAML policy engine, and example scripts, mount a read-only
volume:

```yaml
volumes:
  - ./examples:/app/examples:ro
  - ./policies:/app/policies:ro
```

## Docker Compose

The included `docker-compose.yml` starts a single `agent` service:

```yaml
version: "3.9"
services:
  agent:
    build: .
    environment:
      - OPENAI_API_KEY=${OPENAI_API_KEY}
    volumes:
      - ./examples:/app/examples
```

Override it with a `docker-compose.override.yml` for local secrets or extra
mounts:

```yaml
services:
  agent:
    environment:
      - VAULT_ADDR=https://vault.example.com
    secrets:
      - vault_token

secrets:
  vault_token:
    file: ./secrets/vault_token
```

## Credential Broker

Use `CredentialBroker` with `VaultCredentialSource` to avoid passing raw secrets
through environment variables:

```python
from petfishframework.credentials import CredentialBroker, VaultCredentialSource

broker = CredentialBroker()
source = VaultCredentialSource(
    vault_url="https://vault.example.com",
    token="hvs.CAES...",
)
broker.register_credential_from_vault("openai", source, path="secrets/openai")
```

The Vault source reads the secret once, caches it locally for the lifetime of
the process, and issues scoped, time-limited tokens to tools. The underlying
`hvac` package is optional; install it with:

```bash
pip install petfishframework[vault]
```

## Security Notes

- Keep images small: only production dependencies are installed (`--no-dev`).
- Do not commit API keys, tokens, or `.env` files to version control.
- Mount credential files as read-only volumes or Docker secrets.
- Run the container with the least-privilege user when possible:

  ```dockerfile
  RUN useradd -m appuser
  USER appuser
  ```

- Event logs may contain sensitive arguments. Enable `MASK` policies to
  redact PII and secrets from audit events.
- For Vault, use short-lived tokens and rotate them via your orchestrator.

## Health Checks

Add a simple health check to long-running services:

```dockerfile
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
  CMD python -c "import petfishframework; print(petfishframework.__version__)" || exit 1
```

## Next Steps

- See [architecture.md](architecture.md) for runtime design.
- See [threat-model.md](threat-model.md) for security boundaries.
- See [api.md](api.md) for the full API reference.
