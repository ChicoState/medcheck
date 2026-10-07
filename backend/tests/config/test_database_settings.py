"""Behavioral tests for database settings without mutating Django's settings cache."""

import json
import os
import subprocess
import sys
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parents[2]


def load_database_settings(database_url: str | None) -> subprocess.CompletedProcess[str]:
    """Import settings in a fresh process using only explicit database configuration."""
    environment = {
        "DJANGO_SECRET_KEY": "test-secret-key",
        "PATH": os.environ["PATH"],
        "PYTHONPATH": str(BACKEND_DIR),
    }
    if database_url is not None:
        environment["DATABASE_URL"] = database_url

    return subprocess.run(
        [
            sys.executable,
            "-c",
            (
                "import json; from config.settings import DATABASES; "
                "print(json.dumps(DATABASES['default']))"
            ),
        ],
        cwd=BACKEND_DIR,
        env=environment,
        capture_output=True,
        check=False,
        text=True,
    )


def test_configures_postgresql_from_database_url() -> None:
    result = load_database_settings("postgresql://medcheck:local-password@127.0.0.1:5432/medcheck")

    assert result.returncode == 0
    assert json.loads(result.stdout) == {
        "ENGINE": "django.db.backends.postgresql",
        "HOST": "127.0.0.1",
        "NAME": "medcheck",
        "PASSWORD": "local-password",
        "PORT": "5432",
        "USER": "medcheck",
    }


def test_rejects_a_missing_database_url() -> None:
    result = load_database_settings(None)

    assert result.returncode != 0
    assert "DATABASE_URL" in result.stderr


def test_rejects_a_database_url_without_a_hostname() -> None:
    result = load_database_settings("postgresql://medcheck:local-password@/medcheck")

    assert result.returncode != 0
    assert "DATABASE_URL" in result.stderr
