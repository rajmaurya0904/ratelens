"""Rendering the dataset as CSV, JSON or a Markdown table."""

from __future__ import annotations

import csv
import io
import json
from collections.abc import Sequence

from .model import CSV_FIELDS, RateLimit

FORMATS = ("csv", "json", "markdown")
PIPE = "|"
ESCAPED_PIPE = chr(92) + PIPE


def _cell(value: object) -> str:
    if value is None:
        return ""
    if isinstance(value, float):
        return f"{value:g}"
    return str(value)


def to_csv(limits: Sequence[RateLimit]) -> str:
    out = io.StringIO()
    writer = csv.writer(out, lineterminator="\n")
    writer.writerow(CSV_FIELDS)
    for item in limits:
        row = item.to_dict()
        writer.writerow([_cell(row[f]) for f in CSV_FIELDS])
    return out.getvalue()


def to_json(limits: Sequence[RateLimit]) -> str:
    return json.dumps([item.to_dict() for item in limits], indent=2) + "\n"


def to_markdown(limits: Sequence[RateLimit]) -> str:
    lines = [
        "| api | endpoint | limit | per minute | scope |",
        "| --- | --- | --- | --- | --- |",
    ]
    for item in limits:
        endpoint = item.endpoint.replace(PIPE, ESCAPED_PIPE)
        scope = item.scope.replace(PIPE, ESCAPED_PIPE)
        lines.append(
            f"| {item.api} | `{endpoint}` | {item.allowance} | "
            f"{_cell(item.requests_per_minute)} | {scope} |"
        )
    return "\n".join(lines) + "\n"


def render(limits: Sequence[RateLimit], fmt: str) -> str:
    if fmt == "csv":
        return to_csv(limits)
    if fmt == "json":
        return to_json(limits)
    if fmt == "markdown":
        return to_markdown(limits)
    raise ValueError(f"unknown format {fmt!r}; choose from {', '.join(FORMATS)}")
