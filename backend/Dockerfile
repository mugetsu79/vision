ARG PYTHON_VERSION=3.12

FROM python:${PYTHON_VERSION}-slim-bookworm AS central-builder

ENV UV_LINK_MODE=copy \
    UV_PROJECT_ENVIRONMENT=/app/.venv

WORKDIR /app

RUN apt-get update \
    && apt-get install -y --no-install-recommends build-essential curl git \
    && rm -rf /var/lib/apt/lists/*

COPY pyproject.toml uv.lock alembic.ini README.md ./
COPY src ./src

RUN pip install --no-cache-dir uv \
    && uv sync --locked --no-dev --group runtime --group llm --group model-metadata

FROM python:${PYTHON_VERSION}-slim-bookworm AS central-runtime

RUN apt-get update \
    && apt-get install -y --no-install-recommends curl \
    && rm -rf /var/lib/apt/lists/*

ENV PATH="/app/.venv/bin:$PATH" \
    PYTHONPATH=/app/src

WORKDIR /app

COPY --from=central-builder /app /app

EXPOSE 8000

CMD ["uvicorn", "argus.main:app", "--host", "0.0.0.0", "--port", "8000"]
