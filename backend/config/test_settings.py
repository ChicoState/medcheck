"""Isolated local PostgreSQL settings for Django's test runner."""

import os


os.environ.setdefault(
    "DATABASE_URL", "postgresql://medcheck:medcheck_local_only@127.0.0.1:5432/medcheck"
)
os.environ.setdefault("DJANGO_SECRET_KEY", "test-only-django-secret-key")

from config.settings import *  # noqa: F403
