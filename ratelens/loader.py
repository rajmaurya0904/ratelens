"""CSV loading for ratelens."""

import csv
from pathlib import Path

from ratelens.model import RateLimit


def load_rate_limits(path: str | Path) -> list[RateLimit]:
    """Read a rate‑limit CSV and return a list of :class:`RateLimit` objects.

    The CSV is expected to have the header ``api,endpoint,requests_per_minute,burst``.
    Each row is converted into a :class:`RateLimit` instance.
    """
    limits: list[RateLimit] = []
    # Accept both string paths and Path objects
    path_obj = Path(path)
    with path_obj.open(newline="") as f:
        reader = csv.DictReader(f)
        for row in reader:
            limits.append(
                RateLimit(
                    api=row["api"],
                    endpoint=row["endpoint"],
                    requests_per_minute=int(row["requests_per_minute"]),
                    burst=int(row["burst"]),
                )
            )
    return limits