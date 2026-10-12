"""Tests for ratelens.loader."""

from pathlib import Path

from ratelens.loader import load_rate_limits
from ratelens.model import RateLimit

SAMPLE_CSV = Path(__file__).parent.parent / "ratelens" / "data" / "sample_rate_limits.csv"


def test_returns_expected_count() -> None:
    limits = load_rate_limits(str(SAMPLE_CSV))
    assert len(limits) == 3


def test_returns_rate_limit_instances() -> None:
    limits = load_rate_limits(str(SAMPLE_CSV))
    assert all(isinstance(rl, RateLimit) for rl in limits)


def test_field_values() -> None:
    limits = load_rate_limits(str(SAMPLE_CSV))
    assert limits[0] == RateLimit(
        api="github",
        endpoint="/repos/{owner}/{repo}/issues",
        requests_per_minute=5000,
        burst=1000,
    )
    assert limits[1] == RateLimit(
        api="twitter",
        endpoint="/2/tweets",
        requests_per_minute=300,
        burst=50,
    )
    assert limits[2] == RateLimit(
        api="stripe",
        endpoint="/v1/charges",
        requests_per_minute=100,
        burst=20,
    )