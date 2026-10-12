"""Tests for ratelens.model."""

from ratelens.model import RateLimit


def test_fields() -> None:
    rl = RateLimit(api="github", endpoint="/repos", requests_per_minute=60, burst=10)
    assert rl.api == "github"
    assert rl.endpoint == "/repos"
    assert rl.requests_per_minute == 60
    assert rl.burst == 10


def test_repr() -> None:
    rl = RateLimit(api="github", endpoint="/repos", requests_per_minute=60, burst=10)
    assert repr(rl) == (
        "RateLimit(api='github', endpoint='/repos', "
        "requests_per_minute=60, burst=10)"
    )


def test_equality() -> None:
    rl1 = RateLimit(api="github", endpoint="/repos", requests_per_minute=60, burst=10)
    rl2 = RateLimit(api="github", endpoint="/repos", requests_per_minute=60, burst=10)
    rl3 = RateLimit(api="github", endpoint="/repos", requests_per_minute=30, burst=10)
    assert rl1 == rl2
    assert rl1 != rl3