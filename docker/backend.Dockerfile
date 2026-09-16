# syntax=docker/dockerfile:1.7
# Development-tooling base image only. A runnable Django entrypoint belongs to
# the future backend application, not to infrastructure scaffolding.
FROM ghcr.io/astral-sh/uv:0.9.17 AS uv

FROM python:3.13.11-slim-bookworm AS development

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    UV_LINK_MODE=copy

COPY --from=uv /uv /uvx /bin/

RUN groupadd --gid 10001 app \
    && useradd --uid 10001 --gid app --create-home --shell /usr/sbin/nologin app

WORKDIR /workspace/backend
USER app

# This proves the pinned toolchain is usable without inventing an app project.
CMD ["uv", "--version"]
