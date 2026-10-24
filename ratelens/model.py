"""Data model for ratelens."""

from __future__ import annotations

from dataclasses import asdict, dataclass

CSV_FIELDS = (
    "api",
    "endpoint",
    "requests_per_minute",
    "burst",
    "limit",
    "window_seconds",
    "scope",
    "source",
    "verified",
    "notes",
)


@dataclass(frozen=True)
class RateLimit:
    """One documented limit: ``limit`` requests per ``window_seconds`` on an endpoint.

    ``requests_per_minute`` is the same limit normalised to a minute (it can be
    fractional, e.g. 5000/hour is 83.33). ``burst`` is a back-to-back allowance that the
    provider documents separately from the limit; it is ``None`` when they do not.
    """

    api: str
    endpoint: str
    requests_per_minute: float
    burst: int | None
    limit: int
    window_seconds: int
    scope: str = ""
    source: str = ""
    verified: str = ""
    notes: str = ""

    @property
    def interval_seconds(self) -> float:
        """Average spacing that never exceeds the limit: window / limit."""
        return self.window_seconds / self.limit

    @property
    def allowance(self) -> str:
        """Human form of the limit, e.g. ``5000 per hour`` or ``50 per 10 s``."""
        names = {1: "second", 60: "minute", 3600: "hour", 86400: "day"}
        if self.window_seconds in names:
            return f"{self.limit} per {names[self.window_seconds]}"
        if self.window_seconds % 60 == 0 and self.window_seconds < 3600:
            return f"{self.limit} per {self.window_seconds // 60} min"
        return f"{self.limit} per {self.window_seconds} s"

    def to_dict(self) -> dict[str, object]:
        return asdict(self)
