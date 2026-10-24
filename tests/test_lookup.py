import pytest

from ratelens.loader import load_rate_limits
from ratelens.lookup import (
    apis,
    find_limits,
    get_rate_limit,
    match_quality,
    normalise_path,
    search,
)
from ratelens.model import RateLimit


def rl(api, endpoint, limit=10, window=60, scope="") -> RateLimit:
    return RateLimit(api, endpoint, limit * 60 / window, None, limit, window, scope)


DATA = [
    rl("svc", "/*", 100, scope="all"),
    rl("svc", "/repos/{owner}/{repo}/issues", 20),
    rl("svc", "/repos/octocat/hello/issues", 5),
    rl("svc", "/search/*", 30),
    rl("svc", "/v1/*/search", 7),
    rl("other", "/*", 1),
]


@pytest.mark.parametrize(
    ("raw", "clean"),
    [
        ("/a/b/", "/a/b"),
        ("/a?x=1", "/a"),
        ("/a/b#frag", "/a/b"),
        ("/", "/"),
        ("", "/"),
        ("  /a ", "/a"),
    ],
)
def test_normalise_path(raw, clean) -> None:
    assert normalise_path(raw) == clean


@pytest.mark.parametrize(
    ("pattern", "path", "quality"),
    [
        ("/a/b", "/a/b", 0),
        ("/a/{x}", "/a/zzz", 1),
        ("/a/*", "/a/b/c/d", 2),
        ("/*", "/anything/at/all", 2),
        ("/*", "/", 2),
        ("/a/b", "/a/c", None),
        ("/a/b", "/a", None),
        ("/a", "/a/b", None),
        ("/bot*/send", "/bot123/send", 1),
        ("/bot*/send", "/xbot/send", None),
        ("/v1/*/search", "/v1/anything/search", 1),
    ],
)
def test_match_quality(pattern, path, quality) -> None:
    assert match_quality(pattern, path) == quality


def test_exact_beats_template_beats_wildcard() -> None:
    assert [r.limit for r in find_limits("svc", "/repos/octocat/hello/issues", DATA)] == [5]
    assert [r.limit for r in find_limits("svc", "/repos/a/b/issues", DATA)] == [20]
    assert [r.limit for r in find_limits("svc", "/zzz", DATA)] == [100]


def test_api_name_is_case_insensitive() -> None:
    assert find_limits("SVC", "/zzz", DATA)


def test_unknown_api_or_no_match() -> None:
    assert find_limits("nope", "/x", DATA) == []
    assert find_limits("svc", "/x", [rl("svc", "/only")]) == []


def test_query_strings_and_trailing_slash_ignored() -> None:
    assert find_limits("svc", "/repos/a/b/issues/?page=2", DATA)[0].limit == 20


def test_all_rows_of_the_best_tier_come_back() -> None:
    data = [rl("a", "/x", 1, scope="s1"), rl("a", "/x", 2, scope="s2"), rl("a", "/*", 3)]
    assert [r.limit for r in find_limits("a", "/x", data)] == [1, 2]


def test_broader_adds_less_specific_most_specific_first() -> None:
    got = find_limits("svc", "/search/code", DATA, broader=True)
    assert [r.endpoint for r in got] == ["/search/*", "/*"]


def test_get_rate_limit_returns_first_or_none() -> None:
    assert get_rate_limit("svc", "/repos/a/b/issues", DATA).limit == 20
    assert get_rate_limit("svc", "/search", [rl("svc", "/other")]) is None


def test_apis_counts_sorted() -> None:
    assert apis(DATA) == {"other": 1, "svc": 5}


def test_search_requires_every_word() -> None:
    data = [rl("github", "/search/code", scope="authenticated user"), rl("stripe", "/v1/files")]
    assert [r.api for r in search("github code", data)] == ["github"]
    assert search("github files", data) == []
    assert search("   ", data) == []


def test_bundled_github_issue_path_resolves() -> None:
    rows = find_limits("github", "/repos/octocat/hello/issues", load_rate_limits())
    assert {r.limit for r in rows} == {5000, 60}


def test_bundled_github_code_search_is_ten_a_minute() -> None:
    (row,) = find_limits("github", "/search/code", load_rate_limits())
    assert (row.limit, row.window_seconds) == (10, 60)
