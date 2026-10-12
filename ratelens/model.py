"""Data models for ratelens."""

from dataclasses import dataclass


@dataclass
class RateLimit:
    """A rate limit applied to a single API endpoint."""

    api: str
    endpoint: str
    requests_per_minute: int
    burst: int

    def __repr__(self) -> str:
        return (
            f"RateLimit(api={self.api!r}, endpoint={self.endpoint!r}, "
            f"requests_per_minute={self.requests_per_minute}, "
            f"burst={self.burst})"
        )