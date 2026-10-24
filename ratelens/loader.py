"""Reading and validating rate-limit CSV files."""

from __future__ import annotations

import csv
from importlib import resources
from pathlib import Path

from .model import CSV_FIELDS, RateLimit

REQUIRED = ("api", "endpoint", "limit", "window_seconds")


class DataError(ValueError):
    """The data file is unreadable or a row in it is invalid."""


def default_data_path() -> Path:
    """The dataset shipped inside the package."""
    return Path(str(resources.files("ratelens") / "data" / "rate_limits.csv"))


def _int(value: str, field: str, line: int, *, minimum: int) -> int:
    try:
        number = int(value.strip())
    except ValueError:
        raise DataError(f"line {line}: {field} must be a whole number, got {value!r}") from None
    if number < minimum:
        raise DataError(f"line {line}: {field} must be at least {minimum}, got {number}")
    return number


def parse_row(row: dict[str, str], line: int) -> RateLimit:
    """Turn one CSV row into a :class:`RateLimit`, or raise :class:`DataError`."""
    for field in REQUIRED:
        if not (row.get(field) or "").strip():
            raise DataError(f"line {line}: missing {field}")
    api = row["api"].strip().lower()
    endpoint = row["endpoint"].strip()
    if not endpoint.startswith("/"):
        raise DataError(f"line {line}: endpoint must start with '/', got {endpoint!r}")
    limit = _int(row["limit"], "limit", line, minimum=1)
    window = _int(row["window_seconds"], "window_seconds", line, minimum=1)
    expected = round(limit * 60 / window, 2)
    stated = (row.get("requests_per_minute") or "").strip()
    if stated:
        try:
            rpm = float(stated)
        except ValueError:
            raise DataError(
                f"line {line}: requests_per_minute must be a number, got {stated!r}"
            ) from None
        if abs(rpm - expected) > 0.011:
            raise DataError(
                f"line {line}: requests_per_minute {stated} contradicts "
                f"{limit} per {window} s (which is {expected:g})"
            )
    else:
        rpm = expected
    burst_text = (row.get("burst") or "").strip()
    burst = _int(burst_text, "burst", line, minimum=1) if burst_text else None
    return RateLimit(
        api=api,
        endpoint=endpoint,
        requests_per_minute=rpm,
        burst=burst,
        limit=limit,
        window_seconds=window,
        scope=(row.get("scope") or "").strip(),
        source=(row.get("source") or "").strip(),
        verified=(row.get("verified") or "").strip(),
        notes=(row.get("notes") or "").strip(),
    )


def load_rate_limits(path: str | Path | None = None) -> list[RateLimit]:
    """Read a rate-limit CSV (the bundled dataset when ``path`` is omitted).

    Raises ``FileNotFoundError`` with a readable message if the file is missing and
    :class:`DataError` (naming the line) for a bad header or row.
    """
    target = Path(path) if path is not None else default_data_path()
    if not target.is_file():
        raise FileNotFoundError(f"Data file not found at {target}")
    try:
        handle = target.open(newline="", encoding="utf-8-sig")
    except OSError as exc:
        raise DataError(f"cannot read {target}: {exc.strerror or exc}") from exc
    with handle:
        try:
            return _read(handle, target)
        except UnicodeDecodeError as exc:
            raise DataError(f"{target}: not valid UTF-8 text") from exc


def _read(handle, target: Path) -> list[RateLimit]:
    reader = csv.DictReader(handle)
    header = [h.strip() for h in (reader.fieldnames or [])]
    missing = [f for f in REQUIRED if f not in header]
    if missing:
        raise DataError(
            f"{target}: header is missing {', '.join(missing)} "
            f"(expected columns: {', '.join(CSV_FIELDS)})"
        )
    reader.fieldnames = header
    limits: list[RateLimit] = []
    try:
        for row in reader:
            if row.get(None):
                raise DataError(f"line {reader.line_num}: too many fields")
            if not any((v or "").strip() for v in row.values()):
                continue
            limits.append(parse_row(row, reader.line_num))
    except csv.Error as exc:
        raise DataError(f"{target}: malformed CSV: {exc}") from exc
    return limits
