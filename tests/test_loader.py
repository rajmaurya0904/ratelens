import csv

import pytest

from ratelens.loader import DataError, default_data_path, load_rate_limits, parse_row

HEADER = "api,endpoint,requests_per_minute,burst,limit,window_seconds,scope,source,verified,notes\n"


def write(tmp_path, body: str, header: str = HEADER):
    path = tmp_path / "d.csv"
    path.write_text(header + body, encoding="utf-8")
    return path


def test_bundled_dataset_loads_and_is_substantial() -> None:
    rows = load_rate_limits()
    assert len(rows) >= 30
    assert len({r.api for r in rows}) >= 10
    assert default_data_path().is_file()


def test_every_bundled_row_is_sourced_and_dated() -> None:
    for row in load_rate_limits():
        assert row.source.startswith("https://"), row
        assert len(row.verified) == 10 and row.verified[4] == "-", row
        assert row.endpoint.startswith("/")


def test_bundled_rpm_matches_limit_and_window() -> None:
    for row in load_rate_limits():
        assert row.requests_per_minute == pytest.approx(
            row.limit * 60 / row.window_seconds, abs=0.01
        )


def test_loads_rows_with_types(tmp_path) -> None:
    path = write(tmp_path, "GitHub,/user,83.33,,5000,3600,me,https://e.x,2026-01-01,note\n")
    (row,) = load_rate_limits(path)
    assert row.api == "github"  # lower-cased
    assert row.limit == 5000 and row.window_seconds == 3600
    assert row.burst is None
    assert row.requests_per_minute == pytest.approx(83.33)


def test_rpm_is_derived_when_blank(tmp_path) -> None:
    (row,) = load_rate_limits(write(tmp_path, "a,/x,,10,120,60,,,,\n"))
    assert row.requests_per_minute == 120 and row.burst == 10


def test_minimal_columns_are_enough(tmp_path) -> None:
    path = tmp_path / "m.csv"
    path.write_text("api,endpoint,limit,window_seconds\na,/x,5,1\n")
    (row,) = load_rate_limits(path)
    assert row.requests_per_minute == 300


def test_missing_file_message(tmp_path) -> None:
    with pytest.raises(FileNotFoundError, match="Data file not found at .*nope.csv"):
        load_rate_limits(tmp_path / "nope.csv")


def test_directory_is_not_a_file(tmp_path) -> None:
    with pytest.raises(FileNotFoundError):
        load_rate_limits(tmp_path)


def test_header_missing_column(tmp_path) -> None:
    path = tmp_path / "h.csv"
    path.write_text("api,endpoint\na,/x\n")
    with pytest.raises(DataError, match="missing limit, window_seconds"):
        load_rate_limits(path)


def test_empty_file(tmp_path) -> None:
    path = tmp_path / "e.csv"
    path.write_text("")
    with pytest.raises(DataError, match="header is missing"):
        load_rate_limits(path)


@pytest.mark.parametrize(
    ("body", "message"),
    [
        (",/x,,,5,1,,,,\n", "line 3: missing api"),
        ("a,x,,,5,1,,,,\n", "endpoint must start with '/'"),
        ("a,/x,,,five,1,,,,\n", "limit must be a whole number"),
        ("a,/x,,,0,1,,,,\n", "limit must be at least 1"),
        ("a,/x,,,5,-1,,,,\n", "window_seconds must be at least 1"),
        ("a,/x,,zero,5,1,,,,\n", "burst must be a whole number"),
        ("a,/x,999,,5,60,,,,\n", "contradicts"),
        ("a,/x,abc,,5,60,,,,\n", "requests_per_minute must be a number"),
    ],
)
def test_bad_rows_name_the_line(tmp_path, body, message) -> None:
    path = write(tmp_path, "ok,/y,,,1,1,,,,\n" + body)
    with pytest.raises(DataError, match=message):
        load_rate_limits(path)


def test_error_reports_the_right_line_number(tmp_path) -> None:
    path = write(tmp_path, "a,/x,,,1,1,,,,\nb,/y,,,1,1,,,,\nc,/z,,,oops,1,,,,\n")
    with pytest.raises(DataError, match="line 4"):
        load_rate_limits(path)


def test_blank_lines_are_skipped(tmp_path) -> None:
    rows = load_rate_limits(write(tmp_path, "a,/x,,,1,1,,,,\n,,,,,,,,,\n\nb,/y,,,1,1,,,,\n"))
    assert [r.api for r in rows] == ["a", "b"]


def test_bom_and_quoted_commas(tmp_path) -> None:
    path = tmp_path / "b.csv"
    with path.open("w", newline="", encoding="utf-8-sig") as f:
        w = csv.writer(f)
        w.writerow(["api", "endpoint", "limit", "window_seconds", "notes"])
        w.writerow(["a", "/x", "5", "1", "has, a comma"])
    (row,) = load_rate_limits(path)
    assert row.notes == "has, a comma"


def test_not_utf8(tmp_path) -> None:
    path = tmp_path / "bin.csv"
    path.write_bytes(HEADER.encode() + b"a,/x,,,1,1,\xff\xfe,,,\n")
    with pytest.raises(DataError, match="UTF-8"):
        load_rate_limits(path)


def test_extra_fields(tmp_path) -> None:
    with pytest.raises(DataError, match="too many fields"):
        load_rate_limits(write(tmp_path, "a,/x,,,1,1,,,,,extra\n"))


def test_parse_row_direct() -> None:
    row = parse_row({"api": "A", "endpoint": "/e", "limit": "2", "window_seconds": "4"}, 9)
    assert row.requests_per_minute == 30
