"""Smoke test: package imports cleanly. Replace/extend as modules land."""

import ratelens


def test_version_is_set() -> None:
    assert ratelens.__version__
