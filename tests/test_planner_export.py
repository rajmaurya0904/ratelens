import csv
import io
import json

import pytest

from ratelens.export import render, to_csv, to_json, to_markdown
from ratelens.loader import load_rate_limits
from ratelens.model import CSV_FIELDS, RateLimit
from ratelens.planner import format_duration, group_by_scope, make_plan, min_seconds


def rl(limit, window, burst=None, scope="", endpoint="/x") -> RateLimit:
    return RateLimit("a", endpoint, limit * 60 / window, burst, limit, window, scope)


@pytest.mark.parametrize(
    ("requests", "seconds"),
    [(1, 0), (10, 0), (11, 60), (20, 60), (21, 120), (100, 540)],
)
def test_min_seconds_fixed_window(requests, seconds) -> None:
    assert min_seconds(rl(10, 60), requests) == seconds


def test_burst_smaller_than_limit_slows_the_plan() -> None:
    assert min_seconds(rl(100, 60, burst=10), 25) == 120


def test_min_seconds_rejects_zero() -> None:
    with pytest.raises(ValueError):
        min_seconds(rl(1, 1), 0)


def test_plan_picks_the_slowest_window() -> None:
    plan = make_plan([rl(600, 60), rl(5000, 3600), rl(10000, 86400)], 30000)
    assert plan.binding.window_seconds == 86400
    assert plan.seconds == 2 * 86400
    assert len(plan.windows) == 3


def test_plan_without_wait_has_no_binding_limit() -> None:
    plan = make_plan([rl(100, 60)], 50)
    assert plan.seconds == 0 and plan.binding is None


def test_spacing_is_the_largest_interval() -> None:
    assert make_plan([rl(10, 1), rl(60, 60)], 5).spacing_seconds == 1.0


def test_plan_needs_limits() -> None:
    with pytest.raises(ValueError):
        make_plan([], 5)


def test_group_by_scope_keeps_order() -> None:
    groups = group_by_scope([rl(1, 1, scope="b"), rl(2, 1, scope="a"), rl(3, 1, scope="b")])
    assert list(groups) == ["b", "a"]
    assert [r.limit for r in groups["b"]] == [1, 3]


@pytest.mark.parametrize(
    ("seconds", "text"),
    [
        (0, "0s"),
        (45, "45s"),
        (60, "1m"),
        (750, "12m 30s"),
        (7500, "2h 05m"),
        (7200, "2h"),
        (3 * 86400 + 4 * 3600, "3d 4h"),
        (86400, "1d"),
    ],
)
def test_format_duration(seconds, text) -> None:
    assert format_duration(seconds) == text


def test_csv_export_round_trips_through_the_loader(tmp_path) -> None:
    original = load_rate_limits()
    path = tmp_path / "out.csv"
    path.write_text(to_csv(original), encoding="utf-8")
    assert load_rate_limits(path) == original


def test_csv_has_header_and_one_line_per_row() -> None:
    rows = list(csv.reader(io.StringIO(to_csv(load_rate_limits()))))
    assert tuple(rows[0]) == CSV_FIELDS
    assert len(rows) - 1 == len(load_rate_limits())


def test_json_export_is_valid_and_complete() -> None:
    data = json.loads(to_json(load_rate_limits()))
    assert len(data) == len(load_rate_limits())
    assert set(data[0]) == set(CSV_FIELDS)
    assert isinstance(data[0]["limit"], int)


def test_markdown_table_shape_and_pipe_escape() -> None:
    text = to_markdown([rl(5, 1, scope="a|b")])
    lines = text.splitlines()
    assert lines[0].startswith("| api") and lines[1].startswith("| ---")
    assert "5 per second" in lines[2] and "a\\|b" in lines[2]


def test_render_rejects_unknown_format() -> None:
    with pytest.raises(ValueError, match="unknown format"):
        render([], "yaml")
