"""Infrastructure-only dependency smoke checks; application tests belong elsewhere."""

from importlib.metadata import version


def test_backend_toolchain_dependencies_are_installed() -> None:
    # Test assertions are not production input validation.
    assert version("Django")  # nosec B101
    assert version("djangorestframework")  # nosec B101
