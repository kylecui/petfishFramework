FROM python:3.12-slim

# Non-root user
RUN useradd --create-home --uid 1000 pf
WORKDIR /app

# Install dependencies first (layer caching)
COPY pyproject.toml uv.lock README.md ./
RUN pip install uv && uv sync --no-dev --all-extras

# Copy source
COPY src/ src/
RUN uv pip install --system .

# Switch to non-root
USER pf

# Healthcheck
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD python -c "import petfishframework; print('ok')" || exit 1

# Graceful shutdown
STOPSIGNAL SIGTERM

ENTRYPOINT ["python", "-m", "petfishframework"]
