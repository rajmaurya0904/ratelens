import pytest

from ratelens.model import CSV_FIELDS, RateLimit


def make(**kw) -> RateLimit:
    base = {
        "api": "x",
        "endpoint": "/a",
        "requests_per_minute": 60,
        "burst": None,
        "limit": 60,
        "window_seconds": 60,
    }
    base.update(kw)
    return RateLimit(**base)


@pytest.mark.parametrize(
    ("limit", "window", "text"),
    [
        (5, 1, "5 per second"),
        (30, 60, "30 per minute"),
        (5000, 3600, "5000 per hour"),
        (10000, 86400, "10000 per day"),
        (1200, 300, "1200 per 5 min"),
        (100, 10, "100 per 10 s"),
    ],
)
def test_allowance_text(limit, window, text) -> None:
    assert make(limit=limit, window_seconds=window).allowance == text


def test_interval_is_window_over_limit() -> None:
    assert make(limit=50, window_seconds=10).interval_seconds == pytest.approx(0.2)


def test_frozen_and_equal_by_value() -> None:
    a, b = make(), make()
    assert a == b
    with pytest.raises(AttributeError):
        a.limit = 1  # type: ignore[misc]


def test_to_dict_has_every_csv_field() -> None:
    assert set(make().to_dict()) == set(CSV_FIELDS)
