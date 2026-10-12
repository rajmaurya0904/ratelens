"""CSV loading for ratelens."""

import csv

from ratelens.model import RateLimit


def load_rate_limits(path: str) -> list[RateLimit]:
    """Read a rate-limit CSV and return a list of RateLimit objects.

    Expected CSV header: api,endpoint,requests_per_unit,unit
    """
    limits: list[RateLimit] = []
    with open(path, newline="") as f:
        reader = csv.DictReader(f)
        for row in reader:
            limits.append(
                RateLimit(
                    api=row["api"],
                    endpoint=row["endpoint"],
                    requests_per_unit=int(row["requests_per_unit"]),
                    unit=row["unit"],
                )
            )
    return limits