FROM python:3.13.9-slim

# Ensure stdout/stderr are unbuffered so print() shows up in `docker logs`
ENV PYTHONUNBUFFERED=1

COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

COPY . /app/backend

WORKDIR /app/backend

RUN uv sync --frozen --no-cache

CMD ["/app/backend/.venv/bin/fastapi", "run", "main.py", "--host", "0.0.0.0", "--port", "8000"]