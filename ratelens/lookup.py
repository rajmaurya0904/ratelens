"""Lookup utilities for ratelens."""

from .model import RateLimit


def get_rate_limit(api: str, endpoint: str, data: list[RateLimit]) -> RateLimit | None:
    """Return the RateLimit matching the given api and endpoint, or None."""
    for rate_limit in data:
        if rate_limit.api == api and rate_limit.endpoint == endpoint:
            return rate_limit
    return None