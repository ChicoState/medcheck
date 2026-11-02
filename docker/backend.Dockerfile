# syntax=docker/dockerfile:1.7
FROM ghcr.io/astral-sh/uv:0.9.17 AS uv

FROM python:3.13.16-slim-bookworm AS development

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    UV_LINK_MODE=copy \
    UV_PROJECT_ENVIRONMENT=/opt/venv \
    RUFF_CACHE_DIR=/tmp/ruff-cache

COPY --from=uv /uv /uvx /bin/

RUN apt-get update \
    && apt-get install --yes --no-install-recommends libatomic1 \
    && rm --recursive --force /var/lib/apt/lists/* \
    && groupadd --gid 10001 app \
    && useradd --uid 10001 --gid app --create-home --shell /usr/sbin/nologin app

WORKDIR /workspace/backend

COPY backend/pyproject.toml backend/uv.lock ./
RUN uv sync --all-groups --frozen

COPY backend/ ./
USER app

EXPOSE 8000

CMD ["uv", "run", "python", "manage.py", "runserver", "0.0.0.0:8000"]
