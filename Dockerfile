FROM python:3.12-slim
WORKDIR /app
COPY pyproject.toml uv.lock ./
RUN pip install uv && uv sync --no-dev
COPY src/ src/
RUN uv pip install --system .
ENTRYPOINT ["python", "-m", "petfishframework"]
