"""Tests for ratelens lookup."""

from ratelens.lookup import get_rate_limit
from ratelens.model import RateLimit


def test_get_rate_limit_found() -> None:
    data = [
        RateLimit(api="github", endpoint="/repos", requests_per_minute=60, burst=10),
        RateLimit(api="github", endpoint="/users", requests_per_minute=50, burst=5),
    ]
    result = get_rate_limit("github", "/repos", data)
    assert result is not None
    assert result.api == "github"
    assert result.endpoint == "/repos"
    assert result.requests_per_minute == 60
    assert result.burst == 10


def test_get_rate_limit_not_found() -> None:
    data = [
        RateLimit(api="github", endpoint="/repos", requests_per_minute=60, burst=10),
    ]
    result = get_rate_limit("github", "/users", data)
    assert result is None


def test_get_rate_limit_empty_list() -> None:
    data: list[RateLimit] = []
    result = get_rate_limit("github", "/repos", data)
    assert result is None


def test_get_rate_limit_case_sensitivity() -> None:
    data = [
        RateLimit(api="GitHub", endpoint="/repos", requests_per_minute=60, burst=10),
    ]
    # Different case in api should not match
    result = get_rate_limit("github", "/repos", data)
    assert result is None
    # Different case in endpoint should not match
    result = get_rate_limit("GitHub", "/REPOS", data)
    assert result is None
    # Exact case should match
    result = get_rate_limit("GitHub", "/repos", data)
    assert result is not None
    assert result.api == "GitHub"
    assert result.endpoint == "/repos"