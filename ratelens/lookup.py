"""Finding limits: exact lookup, path-template matching and free-text search."""

from __future__ import annotations

import re
from collections.abc import Iterable

from .model import RateLimit

EXACT, TEMPLATE, WILDCARD = 0, 1, 2  # match quality, best first


def normalise_path(endpoint: str) -> str:
    """Drop any query string or fragment and a trailing slash; keep the leading one."""
    path = re.split(r"[?#]", endpoint.strip(), maxsplit=1)[0]
    if len(path) > 1:
        path = path.rstrip("/")
    return path or "/"


def _segments(path: str) -> list[str]:
    return [s for s in path.split("/") if s]


def match_quality(pattern: str, path: str) -> int | None:
    """How well the dataset ``pattern`` covers ``path``, or None if it does not.

    ``{name}`` matches one path segment, and a trailing ``*`` matches the rest. A
    segment such as ``bot*`` matches any segment starting with ``bot``. Matching on
    segments is case-sensitive, as paths are.
    """
    pat, got = _segments(pattern), _segments(path)
    quality = EXACT
    for i, seg in enumerate(pat):
        if seg == "*" and i == len(pat) - 1:
            return WILDCARD if len(got) >= i else None
        if i >= len(got):
            return None
        if seg == got[i]:
            continue
        if seg.startswith("{") and seg.endswith("}"):
            quality = max(quality, TEMPLATE)
        elif "*" in seg and re.fullmatch(".*".join(map(re.escape, seg.split("*"))), got[i]):
            quality = max(quality, TEMPLATE)
        else:
            return None
    return quality if len(pat) == len(got) else None


def find_limits(
    api: str, endpoint: str, data: Iterable[RateLimit], *, broader: bool = False
) -> list[RateLimit]:
    """All limits for the best-matching entries for ``endpoint`` on ``api``.

    The API name is case-insensitive. An exact entry beats a template (``{owner}``)
    entry, which beats a wildcard (``/*``) entry. Several rows can share an endpoint
    (different windows or plans); they all come back, in dataset order. With
    ``broader`` the less specific matches follow, most specific first, because an
    API-wide limit still applies on top of an endpoint's own.
    """
    wanted = api.strip().lower()
    path = normalise_path(endpoint)
    scored = []
    for item in data:
        if item.api != wanted:
            continue
        quality = match_quality(item.endpoint, path)
        if quality is not None:
            scored.append((quality, item))
    if not scored:
        return []
    best = min(q for q, _ in scored)
    if broader:
        return [
            item
            for _, item in sorted(
                scored, key=lambda pair: (pair[0], -len(_segments(pair[1].endpoint)))
            )
        ]
    return [item for q, item in scored if q == best]


def get_rate_limit(api: str, endpoint: str, data: Iterable[RateLimit]) -> RateLimit | None:
    """The first limit :func:`find_limits` returns, or None."""
    found = find_limits(api, endpoint, data)
    return found[0] if found else None


def apis(data: Iterable[RateLimit]) -> dict[str, int]:
    """API name -> number of rows, sorted by name."""
    counts: dict[str, int] = {}
    for item in data:
        counts[item.api] = counts.get(item.api, 0) + 1
    return dict(sorted(counts.items()))


def search(query: str, data: Iterable[RateLimit]) -> list[RateLimit]:
    """Rows whose api, endpoint, scope or notes contain every word of ``query``."""
    words = query.lower().split()
    if not words:
        return []
    hits = []
    for item in data:
        text = " ".join((item.api, item.endpoint, item.scope, item.notes)).lower()
        if all(w in text for w in words):
            hits.append(item)
    return hits
