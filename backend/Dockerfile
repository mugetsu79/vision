FROM python:3.12-slim AS builder

WORKDIR /app

COPY pyproject.toml alembic.ini ./
COPY src ./src

RUN pip install --no-cache-dir uv
RUN uv sync --all-groups

FROM gcr.io/distroless/python3-debian12

WORKDIR /app

COPY --from=builder /app /app

CMD ["/app/.venv/bin/uvicorn", "argus.main:app", "--host", "0.0.0.0", "--port", "8000"]
