"""Work out how long a batch of requests takes without being throttled."""

from __future__ import annotations

import math
from dataclasses import dataclass

from .model import RateLimit


@dataclass(frozen=True)
class WindowPlan:
    limit: RateLimit
    seconds: float  # minimum time this limit alone forces


@dataclass(frozen=True)
class Plan:
    requests: int
    seconds: float
    binding: RateLimit | None  # the limit that decides the total (None if no wait needed)
    windows: tuple[WindowPlan, ...]

    @property
    def spacing_seconds(self) -> float:
        """Even spacing between requests that stays inside every limit."""
        return max((w.limit.interval_seconds for w in self.windows), default=0.0)


def min_seconds(limit: RateLimit, requests: int) -> float:
    """Shortest time to send ``requests`` requests under one fixed-window limit.

    The first ``limit`` requests can go out at once; each further batch of ``limit``
    has to wait for the next window. If the provider documents a ``burst`` that is
    smaller than the limit, only that many can go out at once per window.
    """
    if requests < 1:
        raise ValueError("requests must be at least 1")
    per_window = min(limit.limit, limit.burst) if limit.burst else limit.limit
    waits = math.ceil(requests / per_window) - 1
    return float(waits * limit.window_seconds)


def make_plan(limits: list[RateLimit], requests: int) -> Plan:
    """Combine several limits that apply together; the slowest one decides."""
    if not limits:
        raise ValueError("no limits to plan against")
    windows = tuple(WindowPlan(item, min_seconds(item, requests)) for item in limits)
    slowest = max(windows, key=lambda w: w.seconds)
    return Plan(requests, slowest.seconds, slowest.limit if slowest.seconds else None, windows)


def format_duration(seconds: float) -> str:
    """``0s``, ``45s``, ``12m 30s``, ``2h 05m``, ``3d 4h``."""
    total = int(round(seconds))
    if total < 60:
        return f"{total}s"
    minutes, sec = divmod(total, 60)
    if minutes < 60:
        return f"{minutes}m {sec:02d}s" if sec else f"{minutes}m"
    hours, minutes = divmod(minutes, 60)
    if hours < 24:
        return f"{hours}h {minutes:02d}m" if minutes else f"{hours}h"
    days, hours = divmod(hours, 24)
    return f"{days}d {hours}h" if hours else f"{days}d"


def group_by_scope(limits: list[RateLimit]) -> dict[str, list[RateLimit]]:
    """Split rows into the situations a caller can be in.

    Rows with the same scope apply together (a per-hour and a per-day cap on the same
    key); rows with different scopes are alternatives (authenticated versus anonymous).
    """
    groups: dict[str, list[RateLimit]] = {}
    for item in limits:
        groups.setdefault(item.scope, []).append(item)
    return groups
