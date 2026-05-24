FROM python:3.13.9-slim

COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

COPY . /app

WORKDIR /app

RUN uv sync --frozen --no-cache

CMD ["/app/.venv/bin/fastapi", "run", "main.py", "--host", "0.0.0.0", "--port", "8000"]